# 검색 재등록 체크리스트

## 사전 확인

- `/` 공개 title이 지분경매 매입센터로 표시됩니다.
- 공개 HTML에 `FactoryPro`와 `wp-content/themes/astra`가 없습니다.
- `https://factorypro.co.kr/sitemap_index.xml` 또는 Rank Math sitemap URL이 200을 반환합니다.
- robots.txt에서 주요 랜딩과 sitemap이 차단되지 않습니다.

## Google Search Console

1. 속성 소유권을 다시 확인합니다.
2. sitemap을 제출합니다.
3. 루트 URL `https://factorypro.co.kr/` 색인 생성 요청을 수행합니다.
4. URL 검사에서 canonical, robots, 모바일 사용성을 확인합니다.
5. 24시간 뒤 색인 상태와 검색 결과 title 반영 여부를 확인합니다.

## Naver Search Advisor

1. 사이트 소유 확인을 다시 수행합니다.
2. sitemap과 robots.txt를 제출합니다.
3. 웹 페이지 수집 요청에 루트 URL을 등록합니다.
4. `site:factorypro.co.kr`로 전체 인식 여부와 최신 title 반영 여부를 분리해서 기록합니다.

## 주의

검색 재등록은 공개 페이지가 24시간 안정적으로 유지된 뒤 수행하는 편이 안전합니다. 캐시나 플러그인 회귀가 남아 있으면 이전 FactoryPro 문구가 다시 수집될 수 있습니다.
