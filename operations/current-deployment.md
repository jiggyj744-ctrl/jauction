# 현재 배포 상태

작성일: 2026-06-30

## 공개 URL

- 메인: `https://jiggyj744-ctrl.github.io/`
- 배포 저장소: `jiggyj744-ctrl.github.io`
- 원본/기획 저장소: `jauction`

## 완료된 작업

- GitHub Pages 루트 정적 랜딩 구축
- 공유물 지분 매입, 지분경매, 상속 지분, 토지 지분, 공유자 갈등, 상가·건물 지분 세부 랜딩 생성
- FAQ와 개인정보 처리방침 생성
- sitemap.xml, robots.txt 생성
- SVG 파비콘 생성
- Lucide 버전 고정
- 문의 폼 honeypot, 개인정보 동의, 1분 rate limit, 문자 fallback 구성
- 공개 HTML에서 과거 브랜드/웹마스터 인증 파일/깨진 한글 패턴 제거 확인

## 검증 결과

- `https://jiggyj744-ctrl.github.io/`: HTTP 200
- `https://jauction-lead-api.jiggyj.workers.dev/health`: HTTP 200
- `/services/share-purchase/`: HTTP 200
- `/services/share-auction/`: HTTP 200
- `/faq/`: HTTP 200
- `/privacy/`: HTTP 200
- `/assets/hero-consultation.png`: HTTP 200
- `/favicon.svg`: HTTP 200
- `/sitemap.xml`: HTTP 200
- `/robots.txt`: HTTP 200

## 브라우저 검수

- 데스크톱: 히어로, 서비스 카드 6개, 문의 폼, 히어로 이미지, 전화 링크 정상
- 모바일: 하단 CTA 표시, 가로 스크롤 없음, 텍스트 줄바꿈 정상
- 폼: 더미 입력 후 문자 링크와 전화 링크 생성 확인
- API 폼: 라이브 더미 입력 후 D1 저장 확인, 검증용 행 삭제 완료
- 콘솔 오류: 없음

## 다음 개선 우선순위

1. Search Console과 Naver Search Advisor에 새 `github.io` 속성 등록
2. sitemap 제출
3. 리드 조회/상태 변경용 운영 스크립트 또는 간단한 관리자 화면 추가
4. 이메일/문자 알림 연결
5. 커스텀 도메인 연결 시 Worker CORS, canonical, sitemap, robots 재생성
