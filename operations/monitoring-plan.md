# 24시간 회귀 모니터링

## 실패 조건

- title에 `공장경매`가 포함됩니다.
- HTML에 `FactoryPro`가 포함됩니다.
- HTML에 `wp-content/themes/astra`가 포함됩니다.
- HTML에 `share-auction-landing`이 없습니다.
- HTML에 `ver=1.0.5`가 없습니다.

## 감시 범위

- URL: `/`, `/?verify=stable_105`
- User-Agent: plain, Chrome desktop, iPhone, bot
- 주기: 15분
- 기간: 24시간
- Codex 자동화 ID: `factorypro-24`

## 실패 시 조치

1. 실패 HTML과 헤더를 저장합니다.
2. `wp_rest_admin.py --list-plugins`로 플러그인 상태를 저장합니다.
3. `share-auction-landing` 활성 여부를 확인합니다.
4. 루트만 실패하면 `factorypro-cache-purge-once`를 활성화해 캐시를 제거합니다.
5. FactoryPro/Astra 계열 플러그인이 active이면 `admin_plugin_actions.py`로 비활성화합니다.
6. `check_public_variants.py`를 다시 실행해 회복 여부를 확인합니다.
