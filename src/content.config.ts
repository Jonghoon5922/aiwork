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
  }),
});

// 프로젝트 — "만든 것들" 주제 아래의 시리즈 하나씩.
const projects = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/projects' }),
  schema: z.object({
    name: z.string(),
    order: z.number().default(99),
    summary: z.string(),
    repo: z.string().optional(),
    stack: z.array(z.string()).default([]),
    status: z.enum(['개발 중', '운영 중', '보류']).default('개발 중'),
  }),
});

// 글 — 프론트매터가 곧 상태 저장소다 (SPEC 7절).
export const KINDS = ['workbook', 'case', 'intro', 'devlog', 'decision', 'release'] as const;

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
  loader: file('./src/content/queue/ai-biseo.yaml'),
  schema: z.object({
    id: z.string(),
    topic: z.string().default('ai-biseo'),
    audience: z.string(),
    task: z.string(),
    question: z.string(),
    status: z.enum(['대기', '작성중', '게시']).default('대기'),
    source: z.string().optional(),
  }),
});

export const collections = { topics, projects, posts, queue };
