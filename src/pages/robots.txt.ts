import type { APIRoute } from 'astro';

// 검색 엔진과 AI 크롤러를 전부 허용한다 (SPEC 5절).
// 이 사이트의 목표가 "AI 에게 물었을 때 인용되는 것" 이라 AI 크롤러를 막을 이유가 없다.
const AI_BOTS = [
  'GPTBot', 'ChatGPT-User', 'OAI-SearchBot',
  'ClaudeBot', 'Claude-Web', 'anthropic-ai',
  'PerplexityBot', 'Perplexity-User',
  'Google-Extended', 'Googlebot', 'Bingbot', 'Yeti', // Yeti = 네이버
  'Applebot', 'Applebot-Extended', 'CCBot', 'cohere-ai', 'Bytespider',
];

export const GET: APIRoute = ({ site }) => {
  const lines = [
    'User-agent: *',
    'Allow: /',
    '',
    ...AI_BOTS.flatMap((bot) => [`User-agent: ${bot}`, 'Allow: /', '']),
    `Sitemap: ${new URL('sitemap-index.xml', site)}`,
    `# LLM 안내: ${new URL('llms.txt', site)}`,
    '',
  ];
  return new Response(lines.join('\n'), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
