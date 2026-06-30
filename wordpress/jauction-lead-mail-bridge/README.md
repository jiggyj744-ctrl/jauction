# Jauction Lead Mail Bridge

Cloudflare Pages/GitHub Pages 랜딩의 상담 접수를 WordPress `wp_mail()`로 전달하는 브리지 플러그인입니다. WP Mail SMTP가 WordPress에 설정되어 있으면 상담 메일도 같은 SMTP 경로로 발송됩니다.

## 역할

- 보호된 REST 주소 `/wp-json/jauction/v1/lead` 제공
- Cloudflare Worker에서 전달한 상담 내용을 `wp_mail()`로 발송
- 수신 이메일, 발신자 이름, 브리지 토큰 관리
- 마지막 발송 상태만 저장

상담 원본 저장 기준은 Cloudflare D1입니다. 이 플러그인은 WordPress에 상담 내용을 목록으로 저장하지 않습니다.

## 설치 후 설정

1. WordPress 관리자에서 플러그인 ZIP을 업로드하고 활성화합니다.
2. `설정 > Jauction Mail`로 이동합니다.
3. 수신 이메일을 확인하고 `테스트 메일 보내기`를 실행합니다.
4. 화면의 REST Endpoint와 Worker Secret Token을 Cloudflare Worker에 설정합니다.

```powershell
cmd /c npx --yes wrangler secret put WORDPRESS_WEBHOOK_TOKEN
cmd /c npx --yes wrangler deploy
```

`WORDPRESS_WEBHOOK_URL`은 Worker `wrangler.jsonc`의 vars 또는 Cloudflare 대시보드 변수로 설정합니다.

```text
https://워드프레스도메인/wp-json/jauction/v1/lead
```

## 확인

```powershell
node workers/lead-api/scripts/leads.mjs notify-config
node workers/lead-api/scripts/leads.mjs notify-test
```

정상 구성 시 `effective_email_channel`은 `wordpress_wp_mail`로 표시됩니다.
