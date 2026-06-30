# 검색 등록 진행 기준

작성일: 2026-06-30

## 현재 결론

현재 공개 주소는 `https://jiggyj744-ctrl.github.io/`입니다. 이 주소는 GitHub 무료 주소라 Cloudflare DNS에서 직접 소유 확인을 할 수 없습니다.

따라서 지금 Google Search Console은 `URL 접두어` 방식으로 등록해야 합니다. 나중에 별도 도메인을 Cloudflare에 연결하면 그때는 Cloudflare DNS에 Google 확인값을 넣는 방식으로 등록할 수 있습니다.

## 지금 바로 가능한 방식

1. Google Search Console에서 `URL 접두어`를 선택합니다.
2. 주소는 `https://jiggyj744-ctrl.github.io/`로 넣습니다.
3. Google이 주는 메타태그 또는 HTML 확인 파일 값을 받습니다.
4. 받은 값을 사이트에 반영합니다.
5. `https://jiggyj744-ctrl.github.io/sitemap.xml`을 제출합니다.

## Cloudflare 방식이 가능한 경우

별도 도메인을 Cloudflare에 연결한 뒤에는 Google Search Console의 `도메인` 방식으로 등록할 수 있습니다. 이때 Google이 주는 TXT 값을 Cloudflare DNS에 추가합니다.

도메인 연결 후에는 아래 항목도 함께 바꿔야 합니다.

- 대표 주소
- sitemap 주소
- robots 주소
- 화면 안 canonical 주소
- 상담 저장 쪽 허용 주소

## 확인값 반영 도구

Google 또는 Naver에서 받은 값을 아래처럼 반영합니다.

```powershell
node tools/apply_search_verification.mjs --google-meta "구글에서 받은 content 값"
node tools/apply_search_verification.mjs --naver-meta "네이버에서 받은 content 값"
node tools/verify_site.mjs
```

잘못 넣었거나 다시 비워야 하면 아래를 실행합니다.

```powershell
node tools/apply_search_verification.mjs --clear
node tools/verify_site.mjs
```

## Naver 진행

사용자가 도메인 또는 사이트 등록 후 Naver 메타태그를 보내주면, 그 값을 반영하고 공개 주소에서 확인한 뒤 Naver Search Advisor에서 소유 확인을 누르면 됩니다.

## 참고

- Google Search Console은 사이트 소유 확인 방법으로 DNS, HTML 파일, HTML 태그 등을 제공합니다.
- Cloudflare에서는 DNS 화면에서 TXT 기록을 추가할 수 있습니다.
