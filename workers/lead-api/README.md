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

## 배포

```powershell
cmd /c npx --yes wrangler d1 migrations apply jauction_leads --remote
cmd /c npx --yes wrangler deploy
```

## 리드 조회

```powershell
cmd /c npx --yes wrangler d1 execute jauction_leads --remote --command "SELECT id, created_at, name, phone, lead_type, review_status FROM leads ORDER BY id DESC LIMIT 20"
```
