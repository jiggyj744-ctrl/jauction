# 최종 검증 기록

작성일: 2026-06-30 KST

## GitHub 정리 결과

| 저장소 | 브랜치 | 상태 |
|---|---|---|
| `jiggyj744-ctrl/jauction` | `master` | 지분경매·공유물 지분 매입 전문 랜딩 저장소로 정리 |
| `keyzard` | `main` | 사용 중지 안내 저장소로 정리 |
| `jiggyj744-ctrl.github.io` | `main` | 루트 프로필/Pages 잔여 파일 정리 |

GitHub Pages API 기준으로 공개 Pages는 비활성 상태다. 검색엔진 색인 삭제 후 새 WordPress 랜딩을 중심으로 운영한다.

## WordPress 라이브 설치

| 항목 | 값 |
|---|---|
| 공개 URL | `https://factorypro.co.kr/` |
| 활성 테마 | `share-auction-landing` |
| 테마 버전 | `1.0.4` |
| 목적 | 지분경매, 공유물 지분 매입, 상속지분, 토지지분 상담 랜딩 |

설치 ZIP: `outputs/share-auction-landing-theme-2026-06-30.zip`

## 충돌 제거

기존 FactoryPro/Astra 랜딩을 되살리거나 공장경매 문구를 주입하던 공개 제어 플러그인은 비활성화했다.

- `FactoryPro Astra Elementor Controls`
- `FactoryPro Site Controls`
- `FactoryPro Factory-Only Controls`
- `FactoryPro Final Header Cleaner`
- `FactoryPro Public Text Cleaner`
- `FactoryPro Content Guard`
- `FactoryPro Header Polish`
- `FactoryPro Public Controls`
- `FactoryPro Platform`
- `FactoryPro Update Guard`
- `FactoryPro Auto Publisher`

`WP Super Cache`는 남아 있으나 루트와 캐시버스터 URL 모두 새 테마 HTML을 반환하는 상태로 확인했다.

## 공개 검증

`https://factorypro.co.kr/` 기준 검증 결과:

- `<title>`: `지분경매·공유물 지분 매입 상담 | 상속지분·토지지분 정리 - 지분경매 매입센터`
- `share-auction-landing`: 있음
- `wp-content/themes/astra`: 없음
- `FactoryPro`: 없음
- `공장경매`: 없음
- `ver=1.0.4`: 있음

User-Agent 변종 검증:

| URL | User-Agent | 새 테마 | Astra | FactoryPro |
|---|---|---:|---:|---:|
| `/` | plain | true | false | false |
| `/` | Chrome desktop | true | false | false |
| `/` | iPhone | true | false | false |
| `/` | bot | true | false | false |
| `/?verify=stable_104` | plain | true | false | false |
| `/?verify=stable_104` | Chrome desktop | true | false | false |
| `/?verify=stable_104` | iPhone | true | false | false |
| `/?verify=stable_104` | bot | true | false | false |

## 브라우저 렌더링 검증

데스크톱 `1440x1000`:

- H1: `지분경매와 공유물 지분 매입, 복잡한 지분을 현실적으로 정리합니다`
- 새 테마 CSS: true
- Astra CSS: false
- FactoryPro 문자열: false
- 공장경매 문자열: false
- 가로 오버플로: false

모바일 `390x844`:

- H1: `지분경매와 공유물 지분 매입, 복잡한 지분을 현실적으로 정리합니다`
- 새 테마 CSS: true
- Astra CSS: false
- FactoryPro 문자열: false
- 공장경매 문자열: false
- 가로 오버플로: false

## 로컬 검증 산출물

- `outputs/factorypro-live-verification-2026-06-30.txt`
- `outputs/factorypro-live-variant-verification-2026-06-30.txt`
- `outputs/factorypro-admin-theme-verification-2026-06-30.txt`
- `outputs/share-auction-landing-theme-2026-06-30.zip`
