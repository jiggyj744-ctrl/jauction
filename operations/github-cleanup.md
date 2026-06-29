# GitHub 저장소 정리 기록

작성일: 2026-06-30

## 정리 목적

기존 `jauction` 저장소는 대량 경매정보 정적 HTML과 생성 산출물을 포함하고 있어, 새 사업 방향인 지분경매·공유물 지분 매입 전문 워드프레스 랜딩과 맞지 않는다.

## 원격 상태

- `jauction`: GitHub API 기준 약 636.8 MiB
- `keyzard`: 소형 자동화 저장소
- `jiggyj744-ctrl.github.io`: 소유권 확인 파일만 존재
- GitHub Pages API 기준 세 저장소 모두 Pages 비활성 상태

## 백업

정리 전 로컬 백업 산출물:

- `outputs/jauction-pre-cleanup-2026-06-30.bundle`
- `outputs/jauction-pre-cleanup-file-inventory-2026-06-30.csv`

## 정리 원칙

- 대량 HTML, 크롤러 산출물, sitemap/feed 파일은 새 루트에 포함하지 않는다.
- 워드프레스 운영은 GitHub Pages가 아니라 별도 호스팅으로 진행한다.
- GitHub에는 기획, 체크리스트, 운영 메모만 유지한다.
- 저장소 용량 자체를 줄이려면 단순 삭제 커밋이 아니라 히스토리 정리 또는 새 저장소 전환이 필요하다.
