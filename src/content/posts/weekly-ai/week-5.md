---
title: 'Weekly AI 5주차: Gemini 4가 검색에 들어왔고, 가격표는 12월에 바뀌어요'
question: 이번 주 AI 소식 중 내 일에 쓸 만한 건 뭔가요
date: '2026-11-16'
topic: weekly-ai
kind: digest
series: Weekly AI
order: 5
summary: 구글이 Gemini 4 Hydrogen을 검색에 넣었고, Carbon은 누구나 쓸 수 있게 됐지만 12월 1일에 값이 두 배가 돼요. 글을 쓰지 않고 판정만 하는 Decisions API, 여러 스레드를 굴리는 Claude Code 프로젝트, llama.cpp 1.0도 함께 정리했어요.
materials: 등록 피드의 지난주 글
tags: [Gemini, 구글 검색, Claude Code, llama.cpp, API 가격]
---

이번 주는 구글이 눈에 띄었어요. Gemini 4가 검색과 API 양쪽으로 한꺼번에 나왔고, 그 옆에서 Claude Code 프로젝트와 llama.cpp도 큰 변화가 있었어요.

### 구글 검색이 여러 조건이 붙은 질문을 한 번에 받아요

출처: [Google 블로그](https://blog.google/products-and-platforms/products/search/gemini-4-hydrogen-search-upgrade/)

구글이 Gemini 4 Hydrogen을 전 세계 구글 검색에 넣었어요. 여러 부분으로 된 질문이나 오타가 섞인 질문도 의도를 읽어 내고, 하위 주제별로 동시에 검색을 돌려 더 많은 링크를 보여 주며, 답에는 비교표와 이미지가 더 많이 들어간다고 해요.

**써 볼 수 있어요.** 직장인이라면 평소에 검색어를 서너 번 바꿔 가며 찾던 일을 한 문장으로 물어보세요. "10명이 쓸 화상회의 도구, 녹화 되고 한국어 자막 되는 것만 비교해 줘"처럼 조건을 전부 붙여서요. 표로 나온 답은 그대로 믿지 말고 표 아래 링크를 한두 개 열어서 가격과 날짜만 확인하세요.

### Gemini 4 Carbon이 모두에게 열렸는데, 12월 1일에 값이 두 배가 돼요

출처: [Simon Willison 블로그](https://simonwillison.net/2026/Nov/12/llm-gemini/)

일부 보안 담당자에게만 열려 있던 Gemini 4 Carbon을 11월 10일부터 누구나 쓸 수 있게 됐어요. Carbon과 Argon은 지금 100만 토큰당 입력 2달러, 출력 10달러인데 12월 1일부터 4달러, 20달러가 되고, 이틀 뒤에 나온 Hydrogen은 1.5달러, 7.5달러예요.

**써 볼 수 있어요.** 개발자라면 11월이 가기 전에 지금 쓰는 프롬프트 몇 개를 Carbon과 Hydrogen에 같이 돌려 보세요. 12월 가격으로 한 달 비용을 다시 계산해 두면, 값이 오른 뒤에 급하게 모델을 바꾸는 일을 피할 수 있어요. 글쓴이는 Hydrogen이 싼 모델이라지만 Claude Haiku 5.5나 GPT-6 Luna보다 15배 비싸다는 점도 짚었어요.

### 글을 쓰지 않고 "예/아니오"만 답하는 API가 구글에서도 나왔어요

출처: [Google 블로그](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-decisions-api/)

Gemini Decisions API는 글, 이미지, 음성, 영상, PDF를 넣고 질문을 최대 1,000개까지 붙이면 답마다 0에서 1 사이의 확신도를 돌려줘요. 질문은 예/아니오, 여럿 중 고르기, 단계별 채점 세 종류이고, 값은 입력 100만 토큰당 0.10달러에 출력은 무료예요.

**써 볼 수 있어요.** 개발자라면 지금 LLM에 "이 문의는 환불 건이야, 배송 건이야?"를 물어 글로 답을 받고 파싱하는 코드가 있는지 찾아보세요. 그런 분류와 검수는 이쪽으로 옮기는 게 맞아요. Google AI Studio에 무료 구간이 있으니 실제 문의 스무 건으로 먼저 돌려 보고, 확신도가 낮은 건만 사람에게 넘기도록 기준을 잡으세요.

### Claude Code 프로젝트가 일을 나눠 여러 스레드로 동시에 굴려요

출처: [Claude 블로그](https://claude.com/resources/articles/projects-redesigned)

프로젝트에 목표를 주면 Claude가 일을 쪼개 스레드에 나눠 맡기고, 결과를 검토해 합쳐요. 스레드 하나하나는 저장소 사본과 자기 브랜치에서 도는 클라우드 세션이고, 모든 스레드가 같은 메모리를 쌓고 꺼내 써요. 지금은 Pro와 Max 구독자 일부에게 베타로 열려 있어요.

**써 볼 수 있어요.** 개발자라면 아직 권한이 없어도 대기 명단에 올려 두고, 그사이에 맡길 일을 하나 골라 두세요. 원문이 든 예처럼 "저장소 세 곳에서 옛 v1 엔드포인트 호출을 걷어내기"같이 저장소별로 갈라지는 일이 잘 맞아요. 스레드마다 세션 하나를 통째로 쓰니 사용량 한도에 빨리 닿는다는 점은 원문도 밝히고 있어요. 처음에는 작은 목표로 시작하세요.

### llama.cpp가 1.0이 됐어요

출처: [Hugging Face 블로그](https://huggingface.co/blog/ggml-org/llama-cpp-v1)

내 컴퓨터에서 모델을 돌릴 때 쓰는 llama.cpp와 그 바탕인 ggml이 v1.0.0을 냈어요. 앞으로 공개 C API가 깨지는 변경은 메이저 버전을 올려서 알리겠다는 약속이고, Homebrew, Winget, Docker 같은 경로로 받을 수 있어요.

**써 볼 수 있어요.** 개발자라면 llama.cpp에 기대는 도구의 버전을 이제 1.x로 고정해 두세요. 업데이트할 때마다 연동이 깨질까 걱정하던 일이 줄어요. 회사 자료를 밖으로 못 보내 AI를 못 쓰던 분이라면, Windows에서는 Winget으로 설치해 로컬 모델부터 하나 돌려 보세요.

다음 주에는 Claude Code 프로젝트가 얼마나 더 열리는지 지켜볼게요. 원문은 한 주에 걸쳐 대상을 넓히겠다고 했어요.
