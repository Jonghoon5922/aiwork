import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { SITE_NAME, SITE_TAGLINE, KIND_LABEL } from '../lib/site';

// llms.txt — LLM 과 AI 검색이 사이트를 한눈에 파악하도록 주제·글 목록을 요약과 함께 내놓는다.
// 빌드 때 자동 생성되므로 글이 늘면 같이 는다. 형식은 llmstxt.org 제안을 따른다.
export const GET: APIRoute = async ({ site }) => {
  const topics = (await getCollection('topics')).sort((a, b) => a.data.order - b.data.order);
  const posts = (await getCollection('posts', ({ data }) => !data.draft)).sort(
    (a, b) => b.data.date.valueOf() - a.data.date.valueOf()
  );
  const abs = (path: string) => new URL(path, site).toString();

  const out: string[] = [
    `# ${SITE_NAME}`,
    '',
    `> ${SITE_TAGLINE}. 직군이 무엇이든 AI 를 내 일에 끌어다 쓰는 법과, AI 와 직접 만든 것들의 기록. 모든 글은 Claude 가 쓰고 마스킹 검사를 거쳐 자동 게시된다.`,
    '',
    '- 언어: 한국어',
    `- 사이트맵: ${abs('/sitemap-index.xml')}`,
    `- RSS: ${abs('/rss.xml')}`,
    `- 이 사이트는 AI가 운영합니다(소개): ${abs('/about/')}`,
    `- 용어집: ${abs('/glossary/')}`,
    '',
  ];

  for (const t of topics) {
    const mine = posts.filter((p) => p.data.topic === t.id);
    out.push(`## ${t.data.name}`, '', `${t.data.summary} (${abs('/' + t.id + '/')})`, '');
    if (mine.length === 0) {
      out.push('- (아직 글이 없음)', '');
      continue;
    }
    for (const p of mine) {
      const q = p.data.question ? ` — 질문: ${p.data.question}` : '';
      out.push(`- [${p.data.title}](${abs('/' + p.id + '/')}): ${p.data.summary} (${KIND_LABEL[p.data.kind]}${p.data.audience ? ', ' + p.data.audience : ''})${q}`);
    }
    out.push('');
  }

  const terms = (await getCollection('terms')).sort((a, b) => a.data.term.localeCompare(b.data.term, 'ko'));
  out.push('## 용어집', '', '글에 나오는 AI 용어의 한 줄 정의. 각 페이지에 비유·내 업무에서 만나는 자리·관련 글이 있다.', '');
  for (const t of terms) out.push(`- [${t.data.term}](${abs('/glossary/' + t.id + '/')}): ${t.data.short}`);
  out.push('');

  return new Response(out.join('\n'), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
