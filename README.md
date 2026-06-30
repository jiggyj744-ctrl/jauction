# Jauction 지분매입 공개 사이트

대표 주소는 `https://jauction-share-acquisition.pages.dev/`입니다. GitHub 주소 `https://jiggyj744-ctrl.github.io/`는 백업 공개 주소로 유지합니다.

공유물 지분, 지분경매, 상속 지분, 토지 지분, 상가·건물 지분을 가진 사람이 상담을 남기도록 만든 정적 랜딩 사이트입니다.

## 운영 범위

- 메인 화면: 지분 매도 상담 유도
- 세부 화면: 공유물 지분 매입, 지분경매, 상속 지분, 토지 지분, 공유자 갈등, 상가·건물 지분
- 상담 접수: Cloudflare Worker와 D1에 저장
- 관리자 화면: `https://jauction-lead-api.jiggyj.workers.dev/admin`
- 검색 등록 자료: `robots.txt`, `sitemap.xml`

## 주요 파일

- `index.html`: 메인 화면
- `services/*/index.html`: 세부 상담 화면
- `faq/index.html`: 자주 묻는 질문
- `privacy/index.html`: 개인정보 안내
- `assets/styles.css`: 화면 스타일
- `assets/main.js`: 상담 접수 화면 동작
- `workers/lead-api/`: 상담 저장과 관리자 화면
- `wordpress/jauction-lead-mail-bridge/`: WP Mail SMTP 연동용 WordPress 플러그인
- `tools/verify_site.mjs`: 로컬 파일 점검
- `tools/verify_live.mjs`: 공개 주소 점검

## 상담 관리

관리자 화면과 관리자 명령은 별도 열쇠로 보호합니다. 열쇠 파일은 `workers/lead-api/.admin-token.local`에만 두고 GitHub에는 올리지 않습니다.

```powershell
node workers/lead-api/scripts/leads.mjs list
node workers/lead-api/scripts/leads.mjs show 1
node workers/lead-api/scripts/leads.mjs update 1 contacted "전화 상담 완료"
node workers/lead-api/scripts/leads.mjs export --limit 100
node workers/lead-api/scripts/leads.mjs notify-config
node workers/lead-api/scripts/leads.mjs notify-test
```

## 상담 알림

상담 저장과 메일 발송은 별도입니다. 상담은 D1에 먼저 저장되고, 메일 발송 설정이 준비된 경우에만 알림 상태가 `sent`로 바뀝니다.

- WordPress 메일 브리지: `WORDPRESS_WEBHOOK_URL`, `WORDPRESS_WEBHOOK_TOKEN`
- Cloudflare 메일: `send_email` 바인딩, `NOTIFY_EMAIL_FROM`, `NOTIFY_EMAIL_TO`
- Resend 메일: `RESEND_API_KEY`, `NOTIFY_EMAIL_FROM`, `NOTIFY_EMAIL_TO`
- 외부 알림 주소: `NOTIFY_WEBHOOK_URL`, 필요 시 `NOTIFY_WEBHOOK_TOKEN`

권장 경로는 WordPress 메일 브리지입니다. WordPress에 `jauction-lead-mail-bridge` 플러그인을 설치하면 Worker가 `/wp-json/jauction/v1/lead`로 상담 내용을 전달하고, 플러그인은 `wp_mail()`을 호출합니다. WP Mail SMTP가 이미 설정되어 있으면 그 발송 경로로 메일이 나갑니다.

Cloudflare 메일 발송은 Cloudflare Email Service에 등록된 발신 도메인 주소에서만 성공합니다. 무료 `github.io` 또는 `pages.dev` 주소만으로는 발신자 도메인 인증을 완료할 수 없습니다.

## 검색 등록

Google Search Console과 Naver Search Advisor에는 대표 주소 `https://jauction-share-acquisition.pages.dev/`를 등록합니다.

확인 태그나 확인 파일을 받으면 아래 도구로 반영합니다.

```powershell
node tools/apply_search_verification.mjs --google-meta "구글에서 받은 content 값"
node tools/apply_search_verification.mjs --naver-meta "네이버에서 받은 content 값"
```

잘못 넣었으면 아래처럼 비웁니다.

```powershell
node tools/apply_search_verification.mjs --clear
```

## 점검

```powershell
node tools/verify_site.mjs
node tools/verify_live.mjs
```
