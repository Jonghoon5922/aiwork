// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// 도메인 aihago.com (2026-10-19 구매). base 없음. public/CNAME 이 GitHub Pages 커스텀 도메인을 고정한다.
export default defineConfig({
  site: 'https://aihago.com',
  trailingSlash: 'always',
  // GitHub Pages 는 /x 를 /x/ 로 301 한다. 처음부터 /x/ 로 링크해 리다이렉트를 없앤다 (url() 이 슬래시를 붙인다).
  integrations: [sitemap()],
});
