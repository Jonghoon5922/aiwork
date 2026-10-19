// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// 사이트 이름·도메인은 미정이다 (SPEC 13절).
// 결정 전까지는 GitHub 프로젝트 사이트 주소로 두고 base 를 쓴다.
// 커스텀 도메인이 붙으면 site 를 바꾸고 base 를 지운다 — 링크는 전부 import.meta.env.BASE_URL 을 거치므로 코드 수정은 없다.
export default defineConfig({
  site: 'https://jonghoon5922.github.io',
  base: '/aiwork',
  trailingSlash: 'never',
  integrations: [sitemap()],
});
