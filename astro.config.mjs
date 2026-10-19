// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// 도메인 aihago.com (2026-10-19 구매). base 없음. public/CNAME 이 GitHub Pages 커스텀 도메인을 고정한다.
export default defineConfig({
  site: 'https://aihago.com',
  trailingSlash: 'never',
  integrations: [sitemap()],
});
