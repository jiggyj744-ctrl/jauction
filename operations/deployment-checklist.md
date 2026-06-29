# 배포 체크리스트

## GitHub 저장소

- 원격 `jauction/master`를 클린 루트로 교체한다.
- 교체 전 `outputs/jauction-pre-cleanup-2026-06-30.bundle` 백업을 보관한다.
- 교체 후 GitHub 저장소 파일 목록이 `public/`, `wordpress/`, `planning/`, `operations/`, `assets/` 중심인지 확인한다.
- 대량 `docs/auction`, `sites`, `feed.xml`, `sitemap.xml`, 인증 HTML 파일이 최신 브랜치에 남아 있지 않은지 확인한다.

## WordPress

- 테마 ZIP 업로드
- 테마 활성화
- SMTP 발송 테스트
- 관리자 이메일 수신 확인
- 전화번호, 사업자 정보, 개인정보처리방침 연결 확인
- SEO 플러그인에서 title/description/canonical 확인

## 검색엔진 전환

- 기존 GitHub Pages가 꺼져 있는지 확인
- 새 도메인의 sitemap만 제출
- 기존 대량 URL은 서버에서 404/410 또는 필요한 301으로 처리
- Google/Naver 삭제 요청만으로 영구 제거가 끝났다고 판단하지 않음

## 상담 전환 검수

- 데스크톱 첫 화면에서 H1과 CTA가 보이는지 확인
- 모바일 첫 화면에서 전화/검토 요청 버튼이 보이는지 확인
- 폼 필수값 검증 확인
- 폼 제출 후 이메일 도착 확인
- 첨부가 필요한 경우 별도 폼 플러그인으로 확장
