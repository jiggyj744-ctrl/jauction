# jauction

지분경매·공유물 지분 매입 전문 워드프레스 랜딩페이지 전환용 저장소입니다.

이 저장소는 기존 대량 경매 HTML, 크롤러 산출물, sitemap/feed 자동 생성물을 보관하지 않습니다. 공개 GitHub 저장소에는 워드프레스 랜딩 제작에 필요한 기획, 운영 메모, 배포 체크리스트만 유지합니다.

## 현재 방향

- 서비스 초점: 지분경매, 공유지분 매입, 상속지분 정리, 공유물분할 경매 검토
- 운영 방식: WordPress 별도 호스팅
- GitHub 역할: 기획 문서, 체크리스트, 정리 이력 보관
- 제외 대상: 대량 경매 상세 HTML, 크롤링 데이터, 검색엔진 인증 파일, 기존 RSS/sitemap 생성물

## 폴더

- `planning/`: 랜딩페이지 기획안과 콘텐츠 구조
- `public/`: 브라우저에서 바로 확인 가능한 정적 랜딩 미리보기
- `assets/`: 랜딩 공통 이미지 자산
- `wordpress/`: 워드프레스 제작/배포 체크리스트와 업로드용 테마
- `operations/`: GitHub 정리, 색인 전환, 운영 메모

## 완성 산출물

- 정적 미리보기: `public/index.html`
- 워드프레스 테마: `wordpress/theme/share-auction-landing/`
- 랜딩 기획안: `planning/share-auction-wordpress-landing-plan.md`
- GitHub 정리 기록: `operations/github-cleanup.md`

## 주의

기존 공개 저장소의 대량 파일은 단순 삭제 커밋만으로 Git 히스토리에서 사라지지 않습니다. GitHub 저장소 용량 자체를 줄이려면 별도 백업 후 orphan/force-push 또는 새 저장소 전환이 필요합니다.
