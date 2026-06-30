# Jauction 리드 접수 API

GitHub Pages 랜딩의 상담 폼을 저장하기 위한 Cloudflare Workers + D1 API입니다.

## 엔드포인트

- Base URL: `https://jauction-lead-api.jiggyj.workers.dev`
- `GET /health`: 상태 확인
- `POST /lead`: 상담 리드 저장

## 저장 DB

- D1 database: `jauction_leads`
- D1 database id: `0e497c26-dc39-4781-ac4a-90f33b195158`

## 보안/품질 기준

- 허용 origin만 CORS 응답
- honeypot 필드(`company_website`)가 있으면 저장하지 않고 accepted 처리
- 이름, 연락처, 상담 유형, 개인정보 동의 필수
- 전화번호 형식 기본 검증
- IP 해시 기준 1시간 5건 제한
- 원본 IP는 저장하지 않고 일 단위 해시만 저장
- 관리자 API는 `ADMIN_TOKEN` Bearer 토큰 필수

## 관리자 API

- `GET /admin/leads?limit=25&status=new&q=검색어`: 리드 목록
- `GET /admin/leads/:id`: 리드 상세
- `PATCH /admin/leads/:id`: 상태와 관리자 메모 변경

상태값:

- `new`
- `reviewing`
- `contacted`
- `offer`
- `hold`
- `closed`
- `spam`

## 배포

```powershell
cmd /c npx --yes wrangler d1 migrations apply jauction_leads --remote
cmd /c npx --yes wrangler deploy
```

## 로컬 운영 CLI

관리자 토큰은 저장소에 커밋하지 않습니다. 로컬에서는 `workers/lead-api/.admin-token.local` 또는 `JAUCTION_ADMIN_TOKEN` 환경 변수를 사용합니다.

```powershell
node workers/lead-api/scripts/leads.mjs list
node workers/lead-api/scripts/leads.mjs show 1
node workers/lead-api/scripts/leads.mjs update 1 contacted "전화 상담 완료"
node workers/lead-api/scripts/leads.mjs export --limit 100
```
