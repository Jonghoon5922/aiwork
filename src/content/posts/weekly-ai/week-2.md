---
title: 'Weekly AI 2주차: 작은 판단은 싸게, 스킬은 공용 규격으로, 에이전트는 울타리 안에서'
question: 이번 주 AI 소식 중 내 일에 쓸 만한 건 뭔가요
date: '2026-10-26'
topic: weekly-ai
kind: digest
series: Weekly AI
order: 2
summary: 이번 주는 분류·라우팅 같은 작은 판단을 따로 떼어 싸고 빠르게 처리하는 Decisions API 정식 출시와, Agent Skills 규격이 리눅스 재단 산하로 간 소식이 눈에 띄었어요. 가중치 공개를 약속한 Kimi K3.1 Pro 와 에이전트를 정책 울타리 안에서 돌리는 NVIDIA OpenShell 까지 네 건을 골랐어요.
materials: 등록 피드의 지난주 글
tags: [Decisions API, Agent Skills, Kimi K3.1, OpenShell, 에이전트]
---

이번 주는 "큰 모델 하나로 다 하기"보다, 작은 판단을 빠르고 싸게 처리하는 전용 API 와 에이전트에 일을 가르치는 규격이 공용 표준으로 가는 흐름이 눈에 띄었어요. 모델 쪽에서는 곧 가중치를 공개하겠다는 Kimi K3.1 Pro 가 최상위권 점수를 냈고, 에이전트를 마음 놓고 돌리기 위한 울타리 도구도 하나 나왔어요.

### 분류·라우팅 같은 작은 판단만 따로 떼는 Decisions API 가 정식 출시됐어요

출처: [OpenAI](https://openai.com/index/decisions-api)

OpenAI 가 10월 22일 Decisions API 를 정식 출시했어요. GPT-6 Luna 를 바탕으로, 질문과 허용되는 답을 정해 주면 확률(predicate)·선택(choice)·점수(score) 세 형태 중 하나로 답하고, 같은 모델을 Responses API 로 쓸 때보다 최대 10배 빠르다고 해요. 베타 이후 JSON 입력과 이미지 첨부, 요청당 질문 400개, GPT-Live 연동이 더해졌어요.

**써 볼 수 있어요.** 개발자라면, 지금 긴 프롬프트로 "이 문의는 어느 팀 담당인가" 같은 분류를 시키고 있는 자리를 하나 고르세요. 그 질문 하나와 허용 답을 정해 Decisions Playground 에 실제 데이터 몇 건을 넣어 보면 됩니다. Box 는 문서 라우팅에서 같은 정확도로 5배 빨랐다고 했고, 확신이 낮은 건은 사람에게 넘기는 식으로 썼어요. 분류를 떼어 내면 본문 생성 쪽 프롬프트도 가벼워져요.

### Agent Skills 규격이 리눅스 재단 산하 공용 표준이 됐어요

출처: [Simon Willison](https://simonwillison.net/2026/Oct/22/donating-agent-skills/) (Anthropic 발표를 인용한 글이에요)

Anthropic 이 Agent Skills 표준을 리눅스 재단 산하 Agentic AI Foundation(AAIF)에 기부한다고 10월 22일 밝혔어요. AAIF 는 Anthropic 이 Block·OpenAI 와 함께 세운 곳이고, MCP 규격도 이미 그곳에 있어요.

**써 볼 수 있어요.** 직장인이라면, 팀에서 반복하는 절차 하나를 SKILL.md 한 장에 적어 두는 것부터 시작하세요. 주간 보고 양식, 회의록 정리 순서처럼 "매번 같은 설명을 하는 일"이 후보예요. 한 회사 제품에 묶인 형식이 아니라 공용 규격이 됐으니, 쓰는 도구가 바뀌어도 그 파일을 그대로 가져갈 수 있어요.

### Kimi K3.1 Pro: 11월 4일 가중치 공개를 약속한 모델이 최상위권 점수를 냈어요

출처: [Simon Willison](https://simonwillison.net/2026/Oct/23/kimi-k31-pro/)

Moonshot 의 Kimi K3.1 Pro 가 10월 23일 Kimi API 에 올라왔고, 가중치는 2026년 11월 4일까지 공개하겠다고 해요. 가격은 입력 100만 토큰당 2달러, 출력 10달러이고, Artificial Analysis 점수는 55로 Claude Opus 5.5(58) 다음이에요.

**써 볼 수 있어요.** 개발자라면, OpenAI 호환 엔드포인트라서 base URL 과 키만 바꾸면 기존 코드로 바로 돌릴 수 있어요. 지금 쓰는 모델에 넣는 프롬프트 열 개를 양쪽에 똑같이 넣고 답과 비용을 나란히 적어 두세요. 가중치가 풀리면 직접 띄우는 선택지가 생기니, 그때 비교할 기준선이 돼요. 2~3배 빠른 Highspeed 판은 값이 두 배라는 점은 알고 고르세요.

### 에이전트가 만질 수 있는 파일·네트워크를 정책으로 묶는 NVIDIA OpenShell

출처: [GitHub (NVIDIA/OpenShell)](https://github.com/NVIDIA/OpenShell)

NVIDIA 가 공개한 OpenShell 은 에이전트마다 격리된 샌드박스를 주고, 어떤 파일을 읽고 어떤 시스템 콜을 부르고 어디로 접속할 수 있는지를 정책으로 정해 커널 수준에서 막는 런타임이에요. 에이전트는 진짜 자격 증명을 보지 못하고 승인된 엔드포인트로 가는 요청에만 붙으며, 정책을 바꿀 때는 새로 열리는 접근을 형식 검증으로 짚어 사람 검토로 넘겨요.

**써 볼 수 있어요.** 개발자라면, 코딩 에이전트를 "일단 다 허용"으로 돌리고 있는 작업 하나를 골라 OpenShell 샌드박스 안에서 다시 돌려 보세요. 기본 이미지는 에이전트가 없는 최소 Ubuntu 라서, 문서의 첫 에이전트 실행 절차를 따라가면 접근이 막힐 때마다 승인하는 흐름이 어떤지 바로 보여요. Linux·Apple Silicon Mac 이 기본이고 Windows 는 WSL 2 로 실험 지원이라는 점, 익명 원격 측정이 기본으로 켜져 있다는 점은 미리 알고 시작하세요.

다음 주에 지켜볼 것: Kimi K3.1 Pro 가중치가 약속대로 11월 4일에 풀리는지요.
