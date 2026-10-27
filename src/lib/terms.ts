import type { CollectionEntry } from 'astro:content';

// 글 본문에 용어나 별칭이 나오면 그 용어를 엮는다. 짧은 별칭(2자 이하)은 오탐이 많아 뺀다.
export function termsInText(text: string, terms: CollectionEntry<'terms'>[]): CollectionEntry<'terms'>[] {
  const lower = text.toLowerCase();
  return terms.filter((t) => {
    const names = [t.data.term, ...t.data.aliases].filter((n) => n.length >= 3);
    return names.some((n) => lower.includes(n.toLowerCase()));
  });
}

export const sortTerms = (terms: CollectionEntry<'terms'>[]) =>
  [...terms].sort((a, b) => a.data.term.localeCompare(b.data.term, 'ko'));

// 매칭에 쓰는 글 텍스트: 제목·요약·태그·FAQ·본문. 태그에만 적힌 용어도 엮이게.
export function postText(post: CollectionEntry<'posts'>): string {
  const d = post.data;
  const faq = (d.faq ?? []).map((f) => `${f.q} ${f.a}`).join(' ');
  return [d.title, d.summary, (d.tags ?? []).join(' '), faq, post.body ?? ''].join(' ');
}
