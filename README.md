# AI 뉴스 브리핑 (ai-briefing)

매일 아침 9시, 그날의 AI 뉴스 3개를 골라 중국어로 요약해서 **카카오톡 「나와의 채팅」** 으로 보내 주는 자동화입니다.
서버 없이 GitHub Actions만으로 돌아갑니다.

- **구분**: 개인 프로젝트 · LIU ZHIYUAN
- **본인 역할**: 정시 전송·중복 방지·모델 재시도 구조를 설계하고, 실제 카카오톡 수신을 직접 확인했습니다. 코드는 AI 코딩 도구를 활용했습니다.

## 동작 흐름
```
Google News RSS ("AI 인공지능", 최근 1일)
  → Gemini가 중요한 뉴스 3개 선택 + 중국어 요약
  → 카카오톡 「나와의 채팅」 전송
  → state.json에 "오늘 보냄" 기록 (중복 전송 방지)
```

## 설계 포인트
- **정시 전송**: Actions의 cron은 늦게 실행될 때가 많아서, 새벽부터 30분마다 실행하고 스크립트가 "8:50 이후 + 오늘 아직 안 보냄"일 때만 보냅니다.
- **실패에 강하게**: Gemini 무료 버전의 503·시간 초과에 지수 백오프로 재시도하고, 모델 3개를 순서대로 시도합니다.
- **키 관리**: API Key·카카오 토큰은 모두 GitHub Secrets에 두고 코드에는 없습니다.
- **의존성 없음**: 표준 라이브러리(`urllib`, `xml`)만 사용합니다.

## 파일 구성
- `briefing.py`: 뉴스 수집 → 요약 → 전송
- `test_briefing.py`: 테스트
- `.github/workflows/briefing.yml`: 예약 실행, 수동 실행(`force`) 지원
- `state.json`: 마지막 전송 기록

## 직접 실행
```bash
DRY=1 FORCE=1 python briefing.py   # 보내지 않고 결과만 출력
```
필요한 환경 변수: `GEMINI_API_KEY`, `KAKAO_REST_KEY`, `KAKAO_REFRESH_TOKEN`, (선택) `KAKAO_CLIENT_SECRET`
