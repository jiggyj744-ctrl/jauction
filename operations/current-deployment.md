# 현재 배포 상태

작성일: 2026-06-30

## 공개 주소

- 대표: `https://jauction-share-acquisition.pages.dev/`
- GitHub 백업: `https://jiggyj744-ctrl.github.io/`
- 관리자: `https://jauction-lead-api.jiggyj.workers.dev/admin`
- 상담 저장: `https://jauction-lead-api.jiggyj.workers.dev/lead`
- sitemap: `https://jiggyj744-ctrl.github.io/sitemap.xml`
- robots: `https://jiggyj744-ctrl.github.io/robots.txt`
- 상담 Worker 배포 버전: `2b215ddd-089a-4b38-b393-9e96f9efd9ab`

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
- 알림 테스트 API: 정상, 현재 발송 제공자 미설정으로 `not_configured`

## 아직 남은 외부 연결

- 실제 이메일 발송용 발신 도메인 또는 Resend 같은 발송 계정 연결
- Google Search Console 등록과 sitemap 제출
- Naver Search Advisor 등록과 sitemap 제출
- 나중에 별도 도메인 연결 시 주소 기준 재생성

현재 사이트는 공개와 접수 기준으로 운영 가능한 상태입니다. 알림 발송 코드는 배포되어 있으며, 실제 메일 발송은 검증된 발신 도메인과 수신 주소 또는 Resend API 키를 연결하면 켤 수 있습니다. 무료 `github.io`와 `pages.dev` 주소는 Cloudflare Email Sending의 발신 도메인으로 등록할 수 없습니다.
