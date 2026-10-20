// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// 도메인 aihago.com (2026-10-19 구매). base 없음. public/CNAME 이 GitHub Pages 커스텀 도메인을 고정한다.
export default defineConfig({
  site: 'https://aihago.com',
  trailingSlash: 'always',
  // GitHub Pages 는 /x 를 /x/ 로 301 한다. 처음부터 /x/ 로 링크해 리다이렉트를 없앤다 (url() 이 슬래시를 붙인다).
  // 소개 글을 주제에서 페이지로 옮겼다. 옛 주소는 넘겨 준다.
  redirects: {
    '/how-this-runs': '/about',
    '/how-this-runs/how-this-site-runs': '/about',
    '/claude-code': '/made',
    // 주제 이름을 가이드로 바꾸면서 주소도 바꿨다 (2026-10-20)
    // 정적 빌드라 동적 리다이렉트가 안 된다. 옛 주소로 나간 글은 하나씩 적는다.
    '/ai-biseo': '/ai-at-work',
    '/ai-biseo/hr-inquiry-reply': '/ai-at-work/hr-inquiry-reply',
    '/ai-biseo/hr-job-posting': '/ai-at-work/hr-job-posting',
  },
  integrations: [sitemap()],
  markdown: {
    // 코드 블록을 사이트 라이트·다크 테마와 맞춘다. 색은 CSS 변수(--shiki-dark)로 나와 global.css 가 고른다.
    shikiConfig: { themes: { light: 'github-light', dark: 'github-dark-dimmed' }, defaultColor: false },
  },
});
