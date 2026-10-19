import rss from '@astrojs/rss';
import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { SITE_NAME, SITE_TAGLINE } from '../lib/site';

export const GET: APIRoute = async ({ site }) => {
  const posts = (await getCollection('posts', ({ data }) => !data.draft)).sort(
    (a, b) => b.data.date.valueOf() - a.data.date.valueOf()
  );
  return rss({
    title: SITE_NAME,
    description: SITE_TAGLINE,
    site: site!,
    items: posts.map((p) => ({
      title: p.data.title,
      description: p.data.summary,
      pubDate: p.data.date,
      link: `/${p.id}/`,
      categories: [p.data.topic, p.data.kind, ...p.data.tags],
    })),
    customData: '<language>ko</language>',
  });
};
