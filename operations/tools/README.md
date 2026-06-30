# 운영 도구

이 폴더는 `factorypro.co.kr`에 올라간 지분경매 매입센터 워드프레스 랜딩을 배포, 복구, 검증하기 위한 최소 운영 도구입니다.

## 도구 목록

- `package_wp_theme.py`: `wordpress/theme/share-auction-landing` 테마를 ZIP으로 패키징합니다.
- `install_wp_theme.py`: 워드프레스 관리자 세션으로 테마 ZIP을 업로드하고 활성화합니다.
- `package_wp_plugin.py`: `share-auction-runtime-guard` 플러그인을 ZIP으로 패키징합니다.
- `install_wp_plugin.py`: 워드프레스 관리자 세션으로 가드 플러그인을 업로드하고 활성화합니다.
- `activate_theme_admin_session.py`: 테마가 이미 설치된 상태에서 `share-auction-landing`만 다시 활성화합니다. 루트 작업 디렉터리의 동일 스크립트와 함께 사용합니다.
- `check_public_page.py`: 공개 루트 페이지의 title, description, 테마 신호, Astra/FactoryPro 잔존 여부를 확인합니다.
- `check_public_variants.py`: `/`와 `/?verify=stable_105`를 plain, Chrome, iPhone, bot User-Agent로 확인합니다.
- `wp_rest_admin.py`: 워드프레스 REST 관리자 세션으로 플러그인 상태와 기본 설정을 점검합니다.
- `admin_plugin_actions.py`: 관리자 화면 action URL로 레거시 FactoryPro 플러그인을 비활성화합니다. 삭제 action은 테마 회귀 부작용이 있어 사용하지 않습니다.
- `remove_legacy_factorypro_plugins.py`: REST 방식 비활성화 보조 도구입니다. nonce 실패 시 `admin_plugin_actions.py`를 우선 사용합니다.

## 정상 기준

- 활성 테마: `share-auction-landing`
- 활성 가드 플러그인: `share-auction-runtime-guard`
- 스타일 버전: `ver=1.0.5`
- 공개 HTML에 `wp-content/themes/astra` 없음
- 공개 HTML에 `FactoryPro` 없음
- 공개 HTML에 `share-auction-landing` 있음

## 실행 순서

```powershell
python .\operations\tools\package_wp_theme.py --source .\wordpress\theme\share-auction-landing --output .\outputs\share-auction-landing.zip
python .\operations\tools\install_wp_theme.py --zip .\outputs\share-auction-landing.zip --force-upload
python .\operations\tools\package_wp_plugin.py --source .\wordpress\plugins\share-auction-runtime-guard --output .\outputs\share-auction-runtime-guard.zip
python .\operations\tools\install_wp_plugin.py --zip .\outputs\share-auction-runtime-guard.zip
python .\operations\tools\check_public_variants.py
python .\operations\tools\check_public_page.py
```

루트 `/`만 예전 FactoryPro HTML을 내보내면 캐시 문제입니다. `factorypro-cache-purge-once`를 한 번 활성화한 뒤 다시 검증합니다.
