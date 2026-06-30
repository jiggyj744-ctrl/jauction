# jauction

지분경매·공유물 지분 매입 상담 사이트의 원본 저장소입니다.

실제 공개 대표 주소는 `https://jauction-share-acquisition.pages.dev/`입니다. GitHub 주소 `https://jiggyj744-ctrl.github.io/`는 백업 공개 주소로 유지합니다. 이 저장소의 `public/` 폴더는 공개 사이트와 같은 화면을 보관합니다.

## 현재 목적

- 공유물 지분을 팔고 싶은 사람 유입
- 지분경매 낙찰 전후 상담 유입
- 상속 지분, 토지 지분, 상가·건물 지분 상담 유입
- 접수된 내용을 검토한 뒤 매입 가능성 또는 보류 사유 안내

## 현재 구성

- `public/`: 공개 화면 복사본
- `workers/lead-api/`: 상담 저장, 관리자 화면, 상담 목록 관리
- `planning/`: 화면 기획과 확장 방향
- `operations/`: 배포, 점검, 검색 재등록 자료
- `tools/verify_live.mjs`: 공개 주소 전체 점검
- `operations/search-registration-cloudflare.md`: Google/Naver 검색 등록 기준

## 공개 주소

- 대표: `https://jauction-share-acquisition.pages.dev/`
- GitHub 백업: `https://jiggyj744-ctrl.github.io/`
- 관리자: `https://jauction-lead-api.jiggyj.workers.dev/admin`
- 상담 저장: `https://jauction-lead-api.jiggyj.workers.dev/lead`
- sitemap: `https://jiggyj744-ctrl.github.io/sitemap.xml`
- robots: `https://jiggyj744-ctrl.github.io/robots.txt`

## 상담 관리

관리자 화면은 별도 열쇠가 있어야 열람할 수 있습니다. 열쇠 파일은 GitHub에 올리지 않습니다.

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

- Cloudflare 메일: `send_email` 바인딩, `NOTIFY_EMAIL_FROM`, `NOTIFY_EMAIL_TO`
- Resend 메일: `RESEND_API_KEY`, `NOTIFY_EMAIL_FROM`, `NOTIFY_EMAIL_TO`
- 외부 알림 주소: `NOTIFY_WEBHOOK_URL`, 필요 시 `NOTIFY_WEBHOOK_TOKEN`

Cloudflare 메일 발송은 Cloudflare Email Service에 등록된 발신 도메인 주소에서만 성공합니다. 무료 `github.io` 또는 `pages.dev` 주소만으로는 발신자 도메인 인증을 완료할 수 없습니다.

## 검색 등록

현재 `github.io` 무료 주소는 Cloudflare DNS 방식으로 Google 소유 확인을 할 수 없습니다. 지금은 Google Search Console의 URL 확인 방식으로 등록하고, 별도 도메인을 Cloudflare에 연결한 뒤에는 DNS 방식으로 진행합니다.

Naver 메타태그를 받으면 `tools/apply_search_verification.mjs`로 반영하고 공개 주소에서 확인합니다.

## 점검 기준

- 공개 화면 12개 주소가 모두 열려야 합니다.
- 예전 업체명, 예전 인증 파일 흔적이 없어야 합니다.
- 상담 접수는 저장되어야 합니다.
- 관리자 목록은 열쇠 없이 열리지 않아야 합니다.
- 시험 상담 자료는 검수 후 삭제되어야 합니다.
