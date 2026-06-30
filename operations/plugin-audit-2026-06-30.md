# 플러그인 감사 기록 - 2026-06-30

## 결론

FactoryPro 계열 플러그인은 공개 사이트 목적과 맞지 않으므로 모두 비활성 상태를 유지합니다. 특히 Astra 전환 코드를 가진 플러그인은 재활성화되어도 `switch_theme('astra')`가 실행되지 않도록 원천 파일에 즉시 반환 방어를 둡니다.

라이브에서는 `share-auction-runtime-guard`를 active로 유지합니다. 이 가드는 FactoryPro 계열 플러그인이 다시 active로 올라오면 `active_plugins` 옵션에서 제거하고 `share-auction-landing` 테마를 다시 고정합니다.

## 레거시 차단 대상

- `factorypro-public-controls/factorypro-public-controls.php`
- `factorypro-astra-elementor-controls/factorypro-astra-elementor-controls.php`
- `factorypro-cache-purge-once/factorypro-cache-purge-once.php`

`factorypro-cache-purge-once`는 루트 캐시 제거가 필요할 때만 일회성으로 활성화하고 자동 비활성화 상태를 확인합니다.

## 활성 유지 후보

- `share-auction-runtime-guard/share-auction-runtime-guard`: FactoryPro 회귀 방지용 런타임 가드
- `seo-by-rank-math/rank-math`: title, description, schema 관리에 필요
- `google-site-kit/google-site-kit`: Search Console/Analytics 연결 확인에 필요
- `wp-mail-smtp/wp_mail_smtp`: 상담 메일 발송 안정성에 필요
- `really-simple-ssl/rlrsssl-really-simple-ssl`: SSL/보안 헤더 관련
- `contact-form-7/wp-contact-form-7`, `wpforms-lite/wpforms`: 현재 랜딩 폼은 테마 내 처리지만 기존 문의 데이터 확인이 끝날 때까지 보류

## 단계적 비활성화 후보

- `astra-sites/astra-sites`: Astra Starter Templates. 현재 랜딩 운영에는 불필요하나, 기존 관리자 화면 의존 여부 확인 후 비활성화합니다.
- `elementor/elementor`, `essential-addons-for-elementor-lite/essential_adons_elementor`, `header-footer-elementor/header-footer-elementor`: 현재 랜딩은 테마 단독 렌더링이므로 필요성이 낮습니다. 기존 페이지/문의/관리 화면 영향 확인 후 1개씩 비활성화합니다.
- `betterdocs/betterdocs`, `wp-kakao-plusfriend/wp-kakao-plusfriend`: 실제 공개 사용 여부 확인 후 정리합니다.

## 재발 방지 기준

- 공개 HTML에 `wp-content/themes/astra`가 보이면 실패입니다.
- 공개 HTML에 `FactoryPro`가 보이면 실패입니다.
- 테마 활성화 후 30초 지연 검증을 반드시 수행합니다.
- 루트만 실패하고 query URL이 통과하면 캐시 퍼지를 먼저 수행합니다.
