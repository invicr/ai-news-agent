# AI News Agent

AX팀 시장 조사용 멀티 에이전트 뉴스 수집 시스템입니다.

## 프로젝트 구조

- `agents/news-collector.md` — 오케스트레이터 (서브에이전트 호출 → 중복 제거 → 최종 JSON 저장)
- `agents/english-news-search.md` — 영문 매체 검색 서브에이전트
- `agents/company-channels-search.md` — 공식 채널 검색 서브에이전트
- `agents/aitimes-collector.md` — AITimes Korea 수집 서브에이전트
- `scripts/scrape_aitimes.py` — AITimes 기사 목록 스크래핑 스크립트

## 출력 JSON 스키마

모든 에이전트는 아래 스키마의 JSON 배열을 반환해야 합니다:

```json
[
  {
    "title": "뉴스 제목",
    "source": "출처 (예: TechCrunch, OpenAI Blog, AITimes)",
    "published_date": "YYYY-MM-DD",
    "url": "기사 URL",
    "why_relevant": "왜 중요한지 한 줄 설명",
    "summary": [
      "- 기사의 핵심적인 기술적 내용이나 영향력을 중심으로 간결하게 요약한 첫 번째 문장.",
      "- 기사의 핵심적인 기술적 내용이나 영향력을 중심으로 간결하게 요약한 두 번째 문장."
    ]
  }
]
```

## 관심 주제

- 에이전트 플랫폼 / 거버넌스 / 개발 환경
- 업무 생산성 포털 (ChatGPT, Gemini, Claude, Perplexity)
- 코딩 어시스턴트 (Cursor, Antigravity, Claude Code, GPT Codex)
- 추론 기술
- 모델 런타임 / 메모리 / 보안 / 운영 인프라
- 오픈소스 모델 / 프레임워크 (Qwen, DeepSeek 등)

## 대상 기업

OpenAI, Anthropic, Perplexity, Google, Microsoft, NVIDIA, AWS, Alibaba, Cursor, Qwen, DeepSeek

## 제외 대상

- 온디바이스 모델 / 모바일 AI 칩 기사
- 주가 / 투자 / 재무 / 소송 기사
- 루머성 / 클릭 유도형 저품질 기사
- AI 윤리 / 사회 논평 (제품 변화 없는 경우)
- 동일 내용 반복 재가공 기사

## 실행 방법

```bash
claude -a agents/news-collector.md -p "오늘 기준으로 최근 1주일 AI 뉴스를 수집해줘"
```
