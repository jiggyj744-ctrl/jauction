# jauction

지분경매·공유물 지분 매입 상담 사이트의 기획, 정적 산출물, 운영 기준을 보관하는 원본 저장소입니다.

실제 공개 메인 사이트는 GitHub 무료 도메인인 `https://jiggyj744-ctrl.github.io/`에서 운영합니다. 이 저장소의 `public/` 폴더는 해당 공개 사이트와 동일한 정적 산출물 미러입니다.

## 현재 방향

- 메인 목적: 공유물 지분, 상속 지분, 토지 지분, 지분경매 사건을 보유한 매도 희망자 유입
- 처리 흐름: 상담 접수 -> 등기·사건자료 검토 -> 권리·점유·공유자 구조 확인 -> 매입 가능성 또는 보류 사유 안내
- 배포 방식: GitHub Pages 정적 사이트
- 리드 저장: Cloudflare Workers + D1
- 현재 공개 URL: `https://jiggyj744-ctrl.github.io/`
- 도메인 연결: 사이트 검수와 접수 백엔드 결정 후 마지막 단계에서 연결

## 저장소 역할

- `planning/`: 랜딩 구조, 전환 문구, 확장 계획
- `public/`: GitHub Pages 공개 산출물 미러
- `workers/lead-api/`: 상담 리드 저장 API
- `operations/`: 배포·검증·색인 재등록 기준

## 공개 산출물

- 메인 랜딩: `public/index.html`
- 세부 랜딩: `public/services/*/index.html`
- FAQ: `public/faq/index.html`
- 개인정보 처리방침: `public/privacy/index.html`
- sitemap: `public/sitemap.xml`
- robots: `public/robots.txt`

## 문의 폼 상태

GitHub Pages는 정적 호스팅이므로 상담 리드 저장은 Cloudflare Workers + D1 API가 담당합니다. 현재 폼은 개인정보 동의, honeypot, 1분 rate limit, D1 저장, 문자 전달 fallback을 포함합니다.

- API: `https://jauction-lead-api.jiggyj.workers.dev/lead`
- Health: `https://jauction-lead-api.jiggyj.workers.dev/health`
- DB: `jauction_leads`

## 제외 대상

- 대량 경매 상세 HTML
- 이전 검색엔진 인증 파일
- RSS/feed 자동 생성물
- 이 사이트 목적과 무관한 과거 브랜드/도메인 운영 파일

## 검증 기준

- 공개 URL이 200을 반환해야 합니다.
- title에 `지분경매·공유물 지분 매입 상담`이 포함되어야 합니다.
- 공개 HTML에 과거 브랜드, 웹마스터 인증 파일, 깨진 한글이 없어야 합니다.
- 모바일에서 가로 스크롤이 없어야 합니다.
- sitemap과 robots가 `https://jiggyj744-ctrl.github.io/` 기준이어야 합니다.
