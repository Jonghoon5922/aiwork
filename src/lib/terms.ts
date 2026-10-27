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
