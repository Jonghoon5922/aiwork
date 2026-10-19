// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// 도메인 aihago.com (2026-10-19 구매). base 없음. public/CNAME 이 GitHub Pages 커스텀 도메인을 고정한다.
export default defineConfig({
  site: 'https://aihago.com',
  trailingSlash: 'never',
  // GitHub Pages 는 /x 를 /x/ 로 301 하므로 x.html 로 뽑아 리다이렉트 없이 바로 서빙되게 한다.
  build: { format: 'file' },
  integrations: [sitemap()],
});
