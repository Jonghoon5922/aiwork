---
title: 'AI하고는 어떻게 내보냈나: git push 한 번이 배포가 되는 세 군데'
question: 개인 사이트를 GitHub Pages랑 Cloudflare로 배포하고 AI가 자동으로 올리게 하려면 어떻게 하나요
date: '2026-11-03'
topic: made
kind: deploy
project: aiwork
until_commit: a5228c8
summary: 사이트는 GitHub Pages(Actions)로, 댓글은 Cloudflare Worker로, 운영 도구는 내 PC의 MCP 서버로 나눠 내보냈어요. 글을 올리는 일은 publish 도구의 git push 한 번이고, 막혔던 곳은 인증·인코딩·폰트·실행 시각이었어요.
materials: aiwork 저장소의 SPEC 과 git 기록
faq:
- {q: 서버를 따로 빌려야 하나요, a: '아니요. 글은 GitHub Pages가 정적 파일로 내보내고, 댓글만 Cloudflare Worker와 D1이 맡아요. 운영 도구는 내 PC에서만 돌아서 호스팅 서버가 없어요.'}
- {q: 글별 OG 이미지를 Actions에서 만들면 안 되나요, a: '이 사이트는 안 돼요. Actions 러너에 한글 폰트가 없어서 제목이 깨져요. 그래서 approve 할 때 로컬에서 그리고, 이미지 파일을 글과 함께 커밋해요.'}
- {q: 예약 실행이 통째로 빠지면 어디부터 보나요, a: 'MCP 서버가 연결 시한 안에 떴는지부터 보세요. 이 사이트는 uv run 으로 띄우던 서버가 잠금 경합으로 30초를 넘겨 주간 실행 두 번이 빠졌고, 가상 환경의 실행 파일을 직접 등록해서 고쳤어요.'}
tags: [배포, GitHub Pages, Cloudflare Workers, MCP, 자동 게시]
---

AI하고는 세 군데로 나눠 내보냈어요. 글은 GitHub Pages에 Actions로, 익명 댓글은 Cloudflare Worker와 D1로, 그리고 사이트를 운영하는 MCP 서버는 서버에 올리지 않고 제 PC에만 둬요. 독자는 aihago.com 으로 들어와 읽기만 하면 되고, 글을 올리는 일은 `publish` 도구가 `git push` 한 번으로 끝내요. push 가 곧 배포예요.

## 내보낸 곳과 방법

처음부터 정한 건 "호스팅 서버를 두지 않는다"였어요. 이 사이트의 도구는 LLM을 부르지도 않고, 글은 Claude가 쓰고 도구는 재료·검사·게시·댓글만 맡아요. 그래서 배포할 것도 세 가지로 줄어요.

- **사이트**: Astro로 만든 정적 사이트. GitHub 저장소의 main 에 push 되면 Actions가 빌드해서 Pages에 올려요.
- **댓글**: Cloudflare Worker 하나와 D1 테이블 하나. Turnstile로 봇을 막고, 금지어·링크 스팸은 Worker가 자동으로 숨겨요.
- **운영 도구**: 파이썬 MCP 서버. Claude 설정에 등록돼 있고, 주간 예약 작업이 이걸 불러 글을 쓰고 올려요.

사이트 배포 워크플로는 이게 전부예요. 손댄 적이 없어요.

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: withastro/action@v3

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

`publish` 도구는 `src/content` 와 글별 OG 이미지 폴더만 `git add` 해서 커밋하고 push 해요. 코드는 건드리지 않아요. 여기에 닿는 글은 이미 마스킹 검사를 통과해 `approve` 된 것뿐이라, 사람 확인 없이 불러도 되게 해 뒀어요. 잘못 나간 글은 `unpublish` 한 뒤 다시 `publish` 하면 내려가요.

## 도메인은 하나만, 주소는 처음부터 끝에 슬래시

github.io 주소는 검색과 AI 인용에서 신뢰를 덜 받아서 커스텀 도메인을 붙였어요. Cloudflare Registrar에서 사고, DNS는 Cloudflare에서 A 레코드 4개와 www CNAME을 "DNS only"로 걸었어요. 저장소의 `public/CNAME` 이 도메인을 고정하고, 옛 github.io 주소는 GitHub가 알아서 넘겨줘요.

주소 규칙은 하나 정했어요. GitHub Pages는 `/x` 를 `/x/` 로 301 리다이렉트하니까, 처음부터 모든 링크를 `/x/` 로 만들어요. Astro 설정에 `trailingSlash: 'always'` 를 두고, 링크는 전부 슬래시를 붙여 주는 헬퍼를 거쳐요. canonical, 사이트맵, llms.txt, RSS 도 같은 모양이에요. 리다이렉트 한 번이 쌓이면 검색 쪽에서 손해라서 이건 미루지 마세요.

## 처음 읽는 사람이 밟는 경로

독자는 가입도 구독도 없이 들어와요. 들어오는 길은 두 가지로 잡았어요. 검색(네이버·구글)과 AI 인용이에요.

- 사이트맵은 빌드할 때 자동으로 나와요. 네이버 서치어드바이저와 구글 서치콘솔에 소유 확인을 하고 사이트맵과 RSS를 제출했어요. 네이버는 등록하지 않으면 거의 가져가지 않아요.
- robots.txt 에서 GPTBot, ClaudeBot, PerplexityBot 같은 AI 크롤러를 허용하고, llms.txt 에 주제와 글 목록, 글마다 한 줄 요약을 빌드 때 넣어요.
- 글 페이지에는 JSON-LD Article 과 FAQ 가 붙고, 공유하면 글 제목이 그려진 OG 이미지가 보여요.

이 중 사람이 직접 한 건 도메인 DNS와 두 검색 서비스 등록뿐이에요. 나머지는 빌드가 만들어요.

## 배포 명령

사이트는 push 하면 끝이라 따로 명령이 없어요. 내보내기 전에 로컬에서 확인할 때만 이렇게 해요.

```bash
npm run build
npm run preview -- --port 4321
```

댓글 Worker는 `worker/` 폴더에서 이렇게 올려요. 인증은 API 토큰을 환경 변수로 넘겨요.

```bash
export CLOUDFLARE_API_TOKEN="$(cat <토큰 파일>)"
npx wrangler deploy
npx wrangler d1 migrations apply aihago-comments --remote
```

MCP 서버는 배포라기보다 등록이에요. Claude 설정에 서버 실행 명령을 적어 두면, 앱이 켜질 때 같이 떠요.

## 생긴 문제와 해결

막힌 곳은 코드보다 주변이었어요.

**wrangler 로그인.** `wrangler login` 의 OAuth 방식은 PowerShell 에서 링크의 `&` 가 깨지고 콜백이 꼬여서 실패했어요. Workers·D1 편집 권한만 준 API 토큰을 만들어 환경 변수로 넘기는 쪽으로 바꿨어요. Turnstile 권한은 토큰에 없어서 위젯만 대시보드에서 만들었어요.

**관리 API가 1010으로 막힘.** 댓글 관리 API를 부를 때 User-Agent 헤더가 없으면 Cloudflare가 1010 오류로 막아요. MCP 쪽 호출에 User-Agent 를 넣어서 풀었어요.

**댓글 테스트 글자가 깨짐.** Git Bash 의 curl 은 콘솔 인코딩으로 본문을 보내서 한글이 깨졌어요. 공개 API 테스트는 UTF-8 로 보내는 파이썬으로 바꿨어요.

**OG 이미지에 한글이 안 나옴.** Actions 러너에는 한글 폰트가 없어요. 그래서 이미지는 빌드에서 만들지 않고, `approve` 할 때 로컬에서 PowerShell 의 System.Drawing 과 맑은 고딕으로 제목을 그려 PNG 로 둬요. 글 페이지는 그 파일이 있으면 쓰고 없으면 기본 이미지로 돌아가요. 생성이 실패해도 `approve` 는 막지 않아요. 배포를 이미지 하나 때문에 멈추게 하지 마세요.

**예약 실행이 통째로 빠짐.** 2026년 11월 2일 주간 실행 두 개가 아무것도 하지 못하고 끝났어요. 앱이 켜지면서 예약 세션 셋이 동시에 `uv run` 으로 MCP 서버를 띄우자 잠금 경합이 생겼고, 30초 연결 시한을 넘겼어요. Claude 설정의 등록을 `uv run` 대신 가상 환경 안의 실행 파일을 직접 부르게 바꿨어요. 대신 의존성을 바꾸면 `uv sync` 를 직접 돌려야 해요.

**PC가 꺼져 있는 시간.** 예약 작업은 데스크톱 앱이 켜져 있을 때만 돌아요. 처음엔 일요일 밤으로 잡았는데 그 시간엔 PC가 꺼져 있어서, Weekly AI 는 월요일 10시, 주간 글은 월요일 10시 반으로 옮겼어요. 꺼져 있으면 다음 실행 때 돌아요.

정리하면, 이 사이트에서 "배포"는 push 한 번이에요. 신경 쓸 곳은 push 앞에 있는 마스킹 검사, 그리고 그 push 를 부르는 예약 실행이 제시간에 뜨느냐예요.
