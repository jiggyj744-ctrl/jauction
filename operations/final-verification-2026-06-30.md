# 최종 검증 기록 - 2026-06-30

대상: `https://factorypro.co.kr/`

## 결론

라이브 사이트는 `share-auction-landing` 테마 `1.0.5`로 활성화되어 있고, 공개 루트와 검증 URL 모두 지분경매·공유물 지분 매입 전문 랜딩을 반환합니다.

## 현재 상태

| 항목 | 결과 |
| --- | --- |
| 활성 테마 | `share-auction-landing` |
| 테마 버전 | `1.0.5` |
| Astra 테마 | inactive |
| FactoryPro 레거시 플러그인 | inactive |
| 런타임 가드 플러그인 | `share-auction-runtime-guard` active |
| Lucide CDN | `lucide@0.468.0` 고정 |
| 문의 폼 방어 | honeypot, 제출시각 검증, 1분 rate limit, 개인정보 동의 |
| 24시간 회귀 모니터링 | `factorypro-24` 활성 |

## 공개 검증

검증 명령:

```powershell
python .\tools\check_public_variants.py
python .\tools\check_public_page.py
```

통과 기준:

- `/`와 `/?verify=stable_105` 모두 `theme=true`
- 모든 User-Agent에서 `astra=false`
- 모든 User-Agent에서 `v105=true`
- 모든 User-Agent에서 `factorypro=false`
- `has_theme=true`
- `has_new_hero=true`
- `has_share_buy=true`
- `has_auction=true`
- `has_old_factory_auction=false`
- `has_astra_theme=false`
- `has_style_105=true`

30초 지연 검증도 같은 기준으로 통과했습니다.

## 폼/자산 검증

`/?verify=stable_105` HTML 직접 검사 결과:

- `share-auction-landing`: 있음
- `ver=1.0.5`: 있음
- `lucide@0.468.0`: 있음
- 버전 없는 Lucide CDN: 없음
- `company_website`: 있음
- `sal_submitted_at`: 있음
- `privacy_agree`: 있음
- `wp-content/themes/astra`: 없음
- `FactoryPro`: 없음

## 처리한 미비점

- 레거시 Astra 강제 플러그인 비활성화 및 source 방어
- `factorypro-public-controls`, `factorypro-astra-elementor-controls` 실행 차단
- `factorypro-platform`, `factorypro-public-controls-runtime`, `factorypro-header-polish` 비활성화
- `share-auction-runtime-guard` 설치 및 활성화
- 로컬 `.git` garbage 정리
- 운영 도구를 `operations/tools`로 정리
- 워드프레스 ZIP 패키징 방식을 플랫 구조로 보정
- 문의 폼 honeypot/rate limit/개인정보 동의 추가
- Lucide 버전 고정
- 24시간 회귀 모니터링 등록

## 남은 보완 계획

1. Search Console과 Naver Search Advisor 재등록 및 sitemap 제출
2. 상담 리드 저장 구조 추가
3. FAQPage, ProfessionalService, BreadcrumbList schema 정리
4. 분야별 랜딩 5-8개 확장
5. Elementor/Astra Starter/폼 플러그인 필요성 확인 후 단계적 비활성화
6. 배포/롤백 runbook을 실제 운영 반복 후 보강
