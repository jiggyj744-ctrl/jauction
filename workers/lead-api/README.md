# Jauction 상담 접수함

GitHub Pages 상담 화면에서 들어온 내용을 저장하고 관리하는 Cloudflare Worker입니다.

## 주소

- 기본 주소: `https://jauction-lead-api.jiggyj.workers.dev`
- 상태 확인: `GET /health`
- 상담 접수: `POST /lead`
- 관리자 화면: `GET /admin`
- 상담 목록: `GET /admin/leads`
- 상담 상세: `GET /admin/leads/:id`
- 상담 상태 변경: `PATCH /admin/leads/:id`

## 저장 공간

- D1 이름: `jauction_leads`
- D1 id: `0e497c26-dc39-4781-ac4a-90f33b195158`

## 보호 기준

- 허용된 공개 주소에서 온 접수만 받습니다.
- 이름, 연락처, 상담 유형, 개인정보 동의는 필수입니다.
- 숨겨진 광고 입력칸이 채워지면 저장하지 않습니다.
- 같은 접속자 기준으로 1시간 5건까지만 받습니다.
- 관리자 화면과 상담 목록은 `ADMIN_TOKEN`으로 보호합니다.
- 상담 접수는 `https://jiggyj744-ctrl.github.io`와 `https://jauction-share-acquisition.pages.dev`에서 허용합니다.

## 상담 알림

새 상담이 저장된 뒤 아래 설정이 있으면 알림을 보냅니다. 설정이 없으면 상담은 정상 저장되고 알림 상태만 `not_configured`로 남습니다.

- 이메일 알림: `RESEND_API_KEY`, `NOTIFY_EMAIL_FROM`, `NOTIFY_EMAIL_TO`
- 외부 알림 주소: `NOTIFY_WEBHOOK_URL`, 필요 시 `NOTIFY_WEBHOOK_TOKEN`

## 반영

```powershell
cmd /c npx --yes wrangler d1 migrations apply jauction_leads --remote
cmd /c npx --yes wrangler deploy
```

## 로컬 관리

관리자 열쇠는 GitHub에 올리지 않습니다. 로컬에서는 `workers/lead-api/.admin-token.local` 또는 `JAUCTION_ADMIN_TOKEN`을 사용합니다.

```powershell
node workers/lead-api/scripts/leads.mjs list
node workers/lead-api/scripts/leads.mjs show 1
node workers/lead-api/scripts/leads.mjs update 1 contacted "전화 상담 완료"
node workers/lead-api/scripts/leads.mjs export --limit 100
```
