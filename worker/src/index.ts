/**
 * 익명 댓글 API (Cloudflare Worker + D1 + Turnstile).
 *
 * 공개:
 *   GET  /comments?post=<id>          숨기지 않은 댓글과 답글
 *   POST /comments  {post, body, token} Turnstile 통과 후 등록. 바로 보인다.
 *                                       금지어·링크 과다·연타는 등록하되 hidden=1 로 숨긴다.
 * 관리 (Authorization: Bearer ADMIN_KEY — MCP 가 쓴다):
 *   GET  /admin/comments?since=<iso>&post=<id>&include_hidden=1
 *   POST /admin/reply {parent, body}   운영자 답글
 *   POST /admin/hide  {id, reason}
 *   POST /admin/unhide {id}
 *
 * 이름·이메일은 받지 않는다. IP 는 해시로만 저장하고 하루마다 소금이 바뀐다.
 */

export interface Env {
  DB: D1Database;
  SITE_ORIGIN: string;
  OWNER_NAME: string;
  MAX_LINKS: string;
  RATE_PER_MINUTE: string;
  TURNSTILE_SECRET?: string;
  ADMIN_KEY?: string;
  FORBIDDEN?: string;
}

const MAX_BODY = 2000;
const MIN_BODY = 2;

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const cors = corsHeaders(req, env);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });

    try {
      let res: Response;
      if (url.pathname === '/comments' && req.method === 'GET') res = await listPublic(url, env);
      else if (url.pathname === '/comments' && req.method === 'POST') res = await create(req, env);
      else if (url.pathname.startsWith('/admin/')) res = await admin(url, req, env);
      else res = json({ error: 'not found' }, 404);
      for (const [k, v] of Object.entries(cors)) res.headers.set(k, v);
      return res;
    } catch (e) {
      const res = json({ error: (e as Error).message }, 500);
      for (const [k, v] of Object.entries(cors)) res.headers.set(k, v);
      return res;
    }
  },
};

// ── 공개 ───────────────────────────────────────────────────────────────

async function listPublic(url: URL, env: Env): Promise<Response> {
  const post = url.searchParams.get('post');
  if (!post) return json({ error: 'post 가 필요해요' }, 400);
  const { results } = await env.DB.prepare(
    'SELECT id, body, created, parent, is_owner FROM comments WHERE post = ? AND hidden = 0 ORDER BY created ASC LIMIT 500',
  ).bind(post).all();
  return json({ post, comments: results, owner: env.OWNER_NAME });
}

async function create(req: Request, env: Env): Promise<Response> {
  const data = (await req.json().catch(() => ({}))) as { post?: string; body?: string; token?: string };
  const post = (data.post || '').trim();
  const body = (data.body || '').trim();
  if (!post || !/^[a-z0-9-]+\/[a-z0-9-]+$/.test(post)) return json({ error: '어느 글인지 알 수 없어요' }, 400);
  if (body.length < MIN_BODY) return json({ error: '내용을 조금 더 적어 주세요' }, 400);
  if (body.length > MAX_BODY) return json({ error: `${MAX_BODY}자까지 쓸 수 있어요` }, 400);

  const ip = req.headers.get('CF-Connecting-IP') || '0.0.0.0';
  if (env.TURNSTILE_SECRET) {
    const ok = await verifyTurnstile(env.TURNSTILE_SECRET, data.token || '', ip);
    if (!ok) return json({ error: '사람인지 확인하지 못했어요. 다시 시도해 주세요' }, 403);
  }

  const ipHash = await hashIp(ip, env.ADMIN_KEY || env.SITE_ORIGIN);
  const now = new Date().toISOString();

  // 자동 숨김 — 지우지 않고 숨긴다. 운영자가 MCP 로 보고 살릴 수 있다.
  let hideReason: string | null = null;
  const links = (body.match(/https?:\/\//gi) || []).length;
  if (links >= Number(env.MAX_LINKS || 2)) hideReason = `링크 ${links}개`;
  const forbidden = (env.FORBIDDEN || '').split(',').map((s) => s.trim()).filter(Boolean);
  const hit = forbidden.find((w) => body.toLowerCase().includes(w.toLowerCase()));
  if (hit) hideReason = '금지어';
  if (!hideReason) {
    const minuteAgo = new Date(Date.now() - 60_000).toISOString();
    const row = await env.DB.prepare('SELECT COUNT(*) AS n FROM comments WHERE ip_hash = ? AND created > ?')
      .bind(ipHash, minuteAgo).first<{ n: number }>();
    if ((row?.n ?? 0) >= Number(env.RATE_PER_MINUTE || 3)) hideReason = '연타';
  }

  const r = await env.DB.prepare(
    'INSERT INTO comments (post, body, created, ip_hash, hidden, hide_reason) VALUES (?, ?, ?, ?, ?, ?) RETURNING id',
  ).bind(post, body, now, ipHash, hideReason ? 1 : 0, hideReason).first<{ id: number }>();

  return json({
    id: r?.id, post, body, created: now, hidden: Boolean(hideReason),
    note: hideReason ? '등록됐지만 검토 뒤에 보여요' : null,
  }, 201);
}

// ── 관리 ───────────────────────────────────────────────────────────────

async function admin(url: URL, req: Request, env: Env): Promise<Response> {
  if (!env.ADMIN_KEY) return json({ error: 'ADMIN_KEY 가 설정되지 않았어요' }, 503);
  const auth = req.headers.get('Authorization') || '';
  if (auth !== `Bearer ${env.ADMIN_KEY}`) return json({ error: 'unauthorized' }, 401);

  if (url.pathname === '/admin/comments' && req.method === 'GET') {
    const since = url.searchParams.get('since');
    const post = url.searchParams.get('post');
    const includeHidden = url.searchParams.get('include_hidden') === '1';
    const where: string[] = ['is_owner = 0'];
    const args: unknown[] = [];
    if (since) { where.push('created > ?'); args.push(since); }
    if (post) { where.push('post = ?'); args.push(post); }
    if (!includeHidden) where.push('hidden = 0');
    const { results } = await env.DB.prepare(
      `SELECT id, post, body, created, parent, hidden, hide_reason, replied FROM comments WHERE ${where.join(' AND ')} ORDER BY created DESC LIMIT 200`,
    ).bind(...args).all();
    return json({ comments: results });
  }

  const data = (await req.json().catch(() => ({}))) as { parent?: number; body?: string; id?: number; reason?: string };

  if (url.pathname === '/admin/reply' && req.method === 'POST') {
    const parent = Number(data.parent);
    const body = (data.body || '').trim();
    if (!parent || !body) return json({ error: 'parent 와 body 가 필요해요' }, 400);
    const p = await env.DB.prepare('SELECT post FROM comments WHERE id = ?').bind(parent).first<{ post: string }>();
    if (!p) return json({ error: '없는 댓글이에요' }, 404);
    const now = new Date().toISOString();
    const r = await env.DB.prepare(
      'INSERT INTO comments (post, body, created, parent, is_owner) VALUES (?, ?, ?, ?, 1) RETURNING id',
    ).bind(p.post, body, now, parent).first<{ id: number }>();
    await env.DB.prepare('UPDATE comments SET replied = 1 WHERE id = ?').bind(parent).run();
    return json({ id: r?.id, post: p.post, parent, created: now }, 201);
  }

  if ((url.pathname === '/admin/hide' || url.pathname === '/admin/unhide') && req.method === 'POST') {
    const id = Number(data.id);
    if (!id) return json({ error: 'id 가 필요해요' }, 400);
    const hide = url.pathname === '/admin/hide';
    await env.DB.prepare('UPDATE comments SET hidden = ?, hide_reason = ? WHERE id = ?')
      .bind(hide ? 1 : 0, hide ? (data.reason || '운영자') : null, id).run();
    return json({ id, hidden: hide });
  }

  return json({ error: 'not found' }, 404);
}

// ── 도우미 ─────────────────────────────────────────────────────────────

async function verifyTurnstile(secret: string, token: string, ip: string): Promise<boolean> {
  if (!token) return false;
  const form = new FormData();
  form.set('secret', secret);
  form.set('response', token);
  form.set('remoteip', ip);
  const res = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', { method: 'POST', body: form });
  const out = (await res.json().catch(() => ({}))) as { success?: boolean };
  return Boolean(out.success);
}

async function hashIp(ip: string, salt: string): Promise<string> {
  const day = new Date().toISOString().slice(0, 10);
  const data = new TextEncoder().encode(`${ip}|${day}|${salt}`);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(digest)].slice(0, 12).map((b) => b.toString(16).padStart(2, '0')).join('');
}

function corsHeaders(req: Request, env: Env): Record<string, string> {
  const origin = req.headers.get('Origin') || '';
  const allowed = [env.SITE_ORIGIN, 'http://localhost:4321'];
  return {
    'Access-Control-Allow-Origin': allowed.includes(origin) ? origin : env.SITE_ORIGIN,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Vary': 'Origin',
  };
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
