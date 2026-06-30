# 저장소 정리 기록

작성일: 2026-06-30

## 정리 목적

`jauction` 저장소를 지분경매·공유물 지분 매입 상담 사이트의 원본/기획 저장소로 재정리했습니다. 실제 공개 사이트는 `jiggyj744-ctrl.github.io` 저장소의 GitHub Pages에서 운영합니다.

## 정리 결과

- 대량 경매 HTML, RSS, 이전 sitemap 성격의 산출물은 현재 작업트리에 포함하지 않습니다.
- 이전 웹마스터 인증 파일은 포함하지 않습니다.
- 현재 공개 랜딩 산출물을 `public/`에 미러링했습니다.
- WordPress 전용 배포 스크립트와 과거 라이브 런타임 대응 문서는 현재 방향과 맞지 않아 제거했습니다.
- 현재 운영 문서는 GitHub Pages 기준으로 다시 작성했습니다.

## 현재 저장소 구조

- `README.md`: 현재 역할과 공개 URL
- `planning/github-pages-share-acquisition-plan.md`: 사이트 기획과 확장안
- `public/`: 공개 랜딩 정적 산출물 미러
- `operations/current-deployment.md`: 라이브 검증 결과
- `operations/seo-reindex-checklist.md`: 검색 재등록 절차

## 공개 배포 기준

- 메인 URL: `https://jiggyj744-ctrl.github.io/`
- sitemap: `https://jiggyj744-ctrl.github.io/sitemap.xml`
- robots: `https://jiggyj744-ctrl.github.io/robots.txt`

## 주의

현재 작업트리에서는 불필요 파일을 제거했지만, 공개 Git 히스토리 자체를 완전히 줄이려면 별도 히스토리 정리나 새 저장소 전환이 필요합니다.
