// 사이트 공통 상수와 링크 도우미.
// base 가 있든 없든(커스텀 도메인 전·후) 링크가 깨지지 않게 모든 내부 링크는 url() 을 거친다.

export const SITE_NAME = 'AI하고'; // 도메인 aihago.com
export const SITE_TAGLINE = 'AI하고 일하고, AI하고 만들어요';

// 검색 엔진 소유 확인 토큰. 서치어드바이저·서치콘솔에서 "HTML 태그" 방식을 고르면 주는 content 값.
// 비어 있으면 태그를 내지 않는다.
export const VERIFY_NAVER = '';
export const VERIFY_GOOGLE = '';

// 익명 댓글 (4단계). Worker 주소와 Turnstile site key. 비어 있으면 댓글 영역을 그리지 않는다.
export const COMMENTS_API = 'https://comments.aihago.com';
export const TURNSTILE_SITE_KEY = '0x4AAAAAAFbJvudDmPpPprxd';

const base = import.meta.env.BASE_URL.replace(/\/$/, '');

// 페이지 링크는 항상 끝에 / 를 붙인다 (trailingSlash: 'always'). 확장자가 있는 파일 링크는 그대로.
export function url(path: string): string {
  if (path === '/' || path === '') return (base || '') + '/';
  let p = `${base}${path.startsWith('/') ? path : `/${path}`}`;
  if (!/\.[a-z0-9]+$/i.test(p) && !p.endsWith('/')) p += '/';
  return p;
}

export const fmtDate = (d: Date) =>
  d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });

export const KIND_LABEL: Record<string, string> = {
  workbook: '워크북',
  case: '사례',
  analysis: '분석',
  design: '설계',
  build: '개발',
  test: '테스트',
  deploy: '배포',
  operate: '운영',
  decision: '결정 기록',
  journal: '회차',
  digest: '소식',
};

// 글 하단 고정 문구 (SPEC 3절). 숨길 일이 아니라 이 사이트의 차별점이다.
export function byline(materials?: string): string {
  const m = materials ? `${materials}에서 재료를 얻어 ` : '';
  return `이 글은 ${m}Claude가 썼고, 마스킹 검사를 거쳐 자동 게시됐습니다.`;
}
