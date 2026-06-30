# 라이브 배포 및 롤백 Runbook

대상: `https://factorypro.co.kr/`

## 현재 운영 기준

- 사이트 목적: 지분경매, 공유물 지분 매입, 상속지분 정리, 토지·아파트·상가 지분 상담 랜딩
- 워드프레스 활성 테마: `share-auction-landing`
- 테마 버전: `1.0.5`
- 활성 가드 플러그인: `share-auction-runtime-guard`
- Lucide CDN: `lucide@0.468.0`
- 공개 루트와 검증 URL 모두 새 랜딩을 반환해야 합니다.

## 배포 절차

1. 저장소 상태 확인

```powershell
git status --short
```

2. 테마 ZIP 생성

```powershell
python .\operations\tools\package_wp_theme.py --source .\wordpress\theme\share-auction-landing --output .\outputs\share-auction-landing.zip
```

3. 워드프레스 업로드 및 활성화

```powershell
python .\operations\tools\install_wp_theme.py --zip .\outputs\share-auction-landing.zip --force-upload
```

4. 런타임 가드 플러그인 업로드 및 활성화

```powershell
python .\operations\tools\package_wp_plugin.py --source .\wordpress\plugins\share-auction-runtime-guard --output .\outputs\share-auction-runtime-guard.zip
python .\operations\tools\install_wp_plugin.py --zip .\outputs\share-auction-runtime-guard.zip
```

5. 레거시 플러그인 상태 확인

```powershell
python .\operations\tools\wp_rest_admin.py --list-plugins
```

FactoryPro/Astra 계열이 active이면 관리자 action 도구로 비활성화합니다. 삭제 action은 테마 회귀 부작용이 있어 사용하지 않습니다.

```powershell
python .\operations\tools\admin_plugin_actions.py
```

6. 공개 검증

```powershell
python .\operations\tools\check_public_variants.py
python .\operations\tools\check_public_page.py
```

7. 지연 검증

```powershell
Start-Sleep -Seconds 30
python .\operations\tools\check_public_variants.py
```

## 캐시 복구

증상: `/?verify=stable_105`는 새 랜딩인데 `/`만 FactoryPro/Astra HTML을 반환합니다.

조치:

1. `factorypro-cache-purge-once/factorypro-cache-purge-once`를 한 번 활성화합니다.
2. 플러그인이 `wp-content/cache/supercache`와 `wp-cache-*`를 삭제한 뒤 자동 비활성화되는지 확인합니다.
3. `/`와 `/?verify=stable_105`를 다시 검사합니다.

## 롤백

문제가 생기면 WordPress 관리자 테마 화면에서 직전 테마를 활성화할 수 있습니다. 단, 현재 사이트 방향은 지분경매 매입센터이므로 롤백 후에는 검색 노출 문구와 sitemap이 FactoryPro로 돌아가지 않았는지 즉시 확인해야 합니다.

## 금지 사항

- FactoryPro/Astra 강제 플러그인을 다시 활성화하지 않습니다.
- 버전 없는 Lucide CDN을 다시 사용하지 않습니다.
- Search Console과 Search Advisor 재등록 전에는 sitemap URL과 robots 상태를 먼저 확인합니다.
