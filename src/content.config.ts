import { defineCollection, z } from 'astro:content';
import { glob, file } from 'astro/loaders';

// 주제 — 사이트의 단위. 글은 반드시 주제 하나에 속한다.
const topics = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/topics' }),
  schema: z.object({
    name: z.string(),
    order: z.number().default(99),
    summary: z.string(),
    // 이 주제의 글이 어디서 나오는지. "이 사이트는 AI가 운영합니다" 글의 재료이기도 하다.
    sources: z.array(z.string()).default([]),
    // 이 주제의 모든 글 하단에 자동으로 붙는 고지문 (예: 투자 연재의 "추천이 아니다").
    notice: z.string().optional(),
    // 홈에서 "누구를 위한 입구인지" 한 줄
    audience: z.string().optional(),
    // 가이드 형식 주제의 차례. 연재(workbook) 글의 order 와 1:1 (첫 항목이 order 1).
    chapters: z.array(z.string()).default([]),
    // 입구·카드에 보이는 아이콘(이모지 하나)과 주제 색(global.css 의 --c-<color>)
    icon: z.string().optional(),
    color: z.enum(['coral', 'violet', 'green', 'amber', 'blue']).default('blue'),
  }),
});

// 고정 페이지 — 소개 같은, 주제에 속하지 않는 글.
const pages = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/pages' }),
  schema: z.object({
    title: z.string(),
    summary: z.string(),
    updated: z.coerce.date().optional(),
    faq: z.array(z.object({ q: z.string(), a: z.string() })).default([]),
  }),
});

// 만든 것 — "쓸 수 있는 것 하나" 가 카드 하나. 종류(type)로 섹션을 나누고 parent 로 묶는다.
export const PROJECT_TYPES = ['service', 'mcp', 'skill', 'tool', 'content'] as const;
export const PROJECT_TYPE_LABEL: Record<(typeof PROJECT_TYPES)[number], string> = {
  service: '서비스', mcp: 'MCP 서버', skill: '스킬', tool: '도구', content: '콘텐츠',
};

const projects = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/projects' }),
  schema: z.object({
    name: z.string(),
    order: z.number().default(99),
    summary: z.string(),
    type: z.enum(PROJECT_TYPES).default('service'),
    // 더 큰 것의 일부라면 그 카드의 slug (예: tokenbill-mcp → tokenbill)
    parent: z.string().optional(),
    // "어떻게 쓰나" 한 줄. 설치 명령이나 주소. 카드에서 바로 복사한다.
    usage: z.string().optional(),
    url: z.string().optional(),
    repo: z.string().optional(),
    stack: z.array(z.string()).default([]),
    status: z.enum(['개발 중', '운영 중', '보류']).default('개발 중'),
    // 이 프로젝트의 글이 가는 주제. 비우면 "만든 것들"(made). 장기 연재는 자기 주제를 가진다.
    topic: z.string().default('made'),
    // 연재 이름(있으면 글에 series 로 붙는다)
    series: z.string().optional(),
  }),
});

// 글 — 프론트매터가 곧 상태 저장소다 (SPEC 7절).
// 프로젝트 글은 교육 자료의 개발 주기 여섯 단계를 그대로 따른다: 분석 → 설계 → 개발 → 테스트 → 배포 → 운영.
export const STAGES = ['analysis', 'design', 'build', 'test', 'deploy', 'operate'] as const;
export const STAGE_LABEL: Record<(typeof STAGES)[number], string> = {
  analysis: '분석', design: '설계', build: '개발', test: '테스트', deploy: '배포', operate: '운영',
};
// 단계마다 글이 답하는 질문 하나. 독자는 이 질문 순서로 프로젝트를 따라 읽는다.
export const STAGE_QUESTION: Record<(typeof STAGES)[number], string> = {
  analysis: '왜 만드나',
  design: '어떻게 만들 건가',
  build: '실제로 어떻게 만들었나',
  test: '제대로 되나',
  deploy: '어떻게 내보냈나',
  operate: '돌려 보니 어떤가',
};
export const KINDS = ['workbook', 'case', ...STAGES, 'decision', 'journal', 'digest'] as const;

const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    // 사람이 검색창이나 AI 에 실제로 치는 문장. 글 하나 = 질문 하나.
    question: z.string().optional(),
    date: z.coerce.date(),
    topic: z.string(),
    kind: z.enum(KINDS),
    summary: z.string(),
    // kind=case
    audience: z.string().optional(),
    // kind=workbook (연재)
    series: z.string().optional(),
    order: z.number().optional(),
    // kind=intro/devlog/decision/release
    project: z.string().optional(),
    until_commit: z.string().optional(),
    // 재료 — 글 하단 고정 문구에 들어간다
    materials: z.string().optional(),
    faq: z.array(z.object({ q: z.string(), a: z.string() })).default([]),
    tags: z.array(z.string()).default([]),
    queue_id: z.string().optional(),
    draft: z.boolean().default(false),
  }),
});

// 사례 큐 — 다음에 쓸 글 후보. 주간 실행이 여기서 하나를 꺼낸다 (SPEC 8절).
const queue = defineCollection({
  loader: file('./src/content/queue/ai-at-work.yaml'),
  schema: z.object({
    id: z.string(),
    topic: z.string().default('ai-at-work'),
    audience: z.string(),
    task: z.string(),
    question: z.string(),
    status: z.enum(['대기', '작성중', '게시']).default('대기'),
    source: z.string().optional(),
  }),
});

export const collections = { topics, pages, projects, posts, queue };
