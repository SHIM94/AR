# 쇼츠 공장 🎬 — AI 쇼츠 대본·자막·썸네일 생성기

주제 한 줄을 넣으면 유튜브 쇼츠 한 편의 **제목·훅·나레이션 대본·SRT 자막·썸네일 문구 3안·해시태그·CTA**를 한 번에 생성하는 웹앱.

본인이 직접 쓰는 도구이자, 월 구독을 붙이면 수익형 마이크로 SaaS가 됩니다.

---

## 1. 로컬에서 실행

```bash
cd shorts-generator
npm install
cp .env.example .env.local      # 그리고 .env.local 에 ANTHROPIC_API_KEY 입력
npm run dev
```

브라우저에서 http://localhost:3000 접속.

- API 키 발급: https://console.anthropic.com → API Keys
- 모델은 기본 `claude-opus-5-5`. 비용을 줄이려면 `.env.local`에 `ANTHROPIC_MODEL=claude-haiku-5-5` 추가.

## 2. Vercel에 무료 배포

1. 이 코드를 GitHub 리포에 올림 (이미 올라가 있다면 생략)
2. https://vercel.com → **Add New → Project** → 리포 선택
3. **Root Directory**를 `shorts-generator` 로 지정
4. **Environment Variables**에 `ANTHROPIC_API_KEY` 추가 (값 = 발급받은 키)
5. **Deploy** 클릭 → 몇 분 뒤 `https://내프로젝트.vercel.app` 로 공개

> Vercel 무료(Hobby) 플랜으로 충분히 시작 가능. API 호출 비용(Anthropic)만 사용량만큼 발생.

## 3. 비용 감각 (대략)

생성 1회당 입력+출력 약 2~4K 토큰.
- `claude-opus-5-5`: 1회 약 **5~15원** 수준
- `claude-haiku-5-5`: 1회 약 **0.5~2원** 수준

→ 월 3,900원 구독자가 하루 10개씩 만들어도 원가는 수백 원. 마진 구조가 성립.

---

## 4. 수익화 로드맵 (다음 단계)

이 MVP는 "무료로 써보게 하는" 단계까지입니다. 돈을 받으려면:

### (a) 사용량 제한 (게이트)
- 비로그인: 하루 3회 무료 (IP/쿠키 기준)
- 그 이상은 가입·결제 유도

### (b) 결제 붙이기
- **국내 타겟**: 토스페이먼츠 / 포트원(아임포트) 정기결제
- **글로벌**: Stripe Billing (월 구독 제품 1개 만들면 끝)

### (c) 로그인 + 사용량 저장
- Supabase(무료 티어) 로 유저·사용횟수 테이블 관리
- `/api/generate` 앞단에서 "남은 횟수" 체크 후 차감

### (d) 차별화 기능 (유료 전환율 올리기)
- 시리즈 모드: 한 주제로 1~10화 자동 생성
- 썸네일 이미지까지 생성 (SVG/이미지 API 연동)
- 업로드 메타데이터(제목/설명/태그) 원클릭 복사 → 유튜브 바로 붙여넣기

이 중 어디든 이어서 개발 가능. "결제부터 붙여줘" 하면 (a)+(b)부터 진행합니다.

---

## 5. 기술 스택

- Next.js 16 (App Router) + React 19 + TypeScript
- Anthropic SDK (`@anthropic-ai/sdk`) — 서버 라우트에서만 호출 (키 노출 없음)
- 외부 DB·인증 없음 (MVP 기준, 위 4번에서 추가)

## 6. 주의

생성되는 투자·재테크 콘텐츠는 **정보 제공용**이며 수익/원금을 보장하지 않습니다.
과장·허위·원금보장 표현은 시스템 프롬프트에서 차단하지만, 업로드 전 반드시 직접 검토하세요.
