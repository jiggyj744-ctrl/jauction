# 현재 배포 상태

작성일: 2026-06-30

## 공개 주소

- 대표: `https://jauction-share-acquisition.pages.dev/`
- GitHub 백업: `https://jiggyj744-ctrl.github.io/`
- 관리자: `https://jauction-lead-api.jiggyj.workers.dev/admin`
- 상담 저장: `https://jauction-lead-api.jiggyj.workers.dev/lead`
- sitemap: `https://jauction-share-acquisition.pages.dev/sitemap.xml`
- robots: `https://jauction-share-acquisition.pages.dev/robots.txt`
- 상담 Worker 최근 코드 배포 버전: `8e918837-1eb5-4b2a-b8cc-ecccce4a4884`
- 상담 Worker secret 반영: 완료, 값은 Worker secret으로만 보관

## 완료된 작업

- GitHub 무료 주소 기준 지분매입 랜딩 사이트 구성
- 메인 화면, FAQ, 개인정보 안내, 6개 세부 상담 화면 구성
- 상담 접수 저장 연결
- 관리자 화면과 관리자 목록 보호
- 상담 상태 변경과 관리자 메모 저장
- 상담 알림 상태 저장 칸 추가
- 이메일 또는 외부 알림 주소 연결 준비
- Cloudflare Email `send_email` 바인딩 추가
- 관리자 알림 설정 점검과 테스트 발송 기능 추가
- WordPress `wp_mail()` 브리지 알림 코드 추가
- WordPress MU 플러그인 배치 파일 생성
- 알림 성공 오인 방지: WordPress 응답이 JSON이고 `ok: true`, `mail_sent: true`일 때만 성공 처리
- 자동 알림 순서 보완: WordPress 실패 시 Cloudflare Email, Resend, webhook 순서로 가능한 채널 시도
- 공개 주소 전체 점검 도구 추가
- Cloudflare Pages 대표 배포 생성
- Cloudflare Pages 주소에서 상담 접수 허용
- 예전 업체명, 예전 인증 파일 흔적 제거 확인

## 2026-06-30 최종 점검 결과

- 공개 화면 12개 주소: 정상
- 메인 상담 접수 주소 포함 여부: 정상
- 관리자 화면: 정상
- 관리자 목록 무단 접근 차단: 정상
- 상담 저장 공간 새 칸 적용: 정상
- 시험 상담 접수: 정상
- 시험 상담 삭제 완료
- 이후 별도 상담 접수 1건 보존
- 예전 업체명, 예전 인증 흔적: 없음
- Cloudflare Pages 주소 접속: 정상
- Cloudflare Pages 출처 상담 접수: 정상
- sitemap, robots, canonical Cloudflare 대표 주소 기준 반영: 정상
- 상담 Worker 새 배포: 정상
- Cloudflare Email 바인딩 인식: 정상
- 알림 설정 점검 API: 정상
- 알림 설정 API: 정상, 자동 모드에서 `wordpress_wp_mail,cloudflare_email` 시도 대상으로 표시
- 알림 테스트 API: 호출 정상, 발송 결과는 `failed / wordpress_wp_mail,cloudflare_email`
- 실제 `/lead` 접수: 저장 정상, 발송 결과는 `failed / wordpress_wp_mail,cloudflare_email`
- WordPress 브리지 공개 REST: 미활성 또는 차단 상태. `/wp-json/jauction/v1/lead`가 실제 JSON 성공 응답을 반환하지 않음
- Cloudflare Email: 바인딩과 발신/수신 설정은 존재하지만 실제 발송은 Cloudflare 내부 오류로 실패
- 시험 상담 삭제 완료 후 D1 보존 상담: 1건

## 아직 남은 외부 연결

- Google Search Console 등록과 sitemap 제출
- Naver Search Advisor 등록과 sitemap 제출
- 나중에 별도 도메인 연결 시 주소 기준 재생성
- WordPress 실제 운영 사이트에 `jauction-lead-mail-bridge` 설치와 REST 보호 예외 적용
- Cloudflare Email Sending의 발신 도메인 활성화 또는 대체 메일 API/SMTP 값 확보
- 메일 발송 성공 후 운영 메일함 수신 확인

현재 사이트는 공개 화면, 상담 저장, 관리자 확인 기준으로 운영 가능합니다. 메일 알림은 실패를 정확히 기록하도록 보완했지만, 실제 발송은 WordPress 브리지 활성화 또는 Cloudflare Email/대체 메일 채널 정상화가 끝나야 운영 완료로 볼 수 있습니다.
