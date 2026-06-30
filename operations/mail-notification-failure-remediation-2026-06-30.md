# 메일 알림 실패 보완 보고서

작성일: 2026-06-30

## 확인한 현재 상태

- 상담 접수 `/lead` 저장은 정상입니다.
- 관리자 알림 설정 API는 정상 응답합니다.
- 자동 알림 모드에서 현재 시도 대상은 `wordpress_wp_mail,cloudflare_email`입니다.
- WordPress 경로는 공개 REST 브리지 라우트가 실제 JSON 성공 응답을 반환하지 않아 실패합니다.
- Cloudflare Email 경로는 바인딩과 발신/수신 설정은 존재하지만 실제 발송 단계에서 내부 오류로 실패합니다.
- 기존 SMTP 값은 인증 실패가 확인되어 운영 발송 채널로 사용할 수 없습니다.

## 보완한 내용

- WordPress가 단순 2xx HTML을 반환해도 성공으로 기록하지 않도록 수정했습니다.
- WordPress 응답이 JSON이고 `ok: true`, `mail_sent: true`일 때만 `sent`로 기록합니다.
- 자동 모드는 WordPress 실패 후 Cloudflare Email, Resend, webhook 순서로 가능한 채널을 계속 시도합니다.
- 모든 채널이 실패하면 상담은 저장하고 `notification_status=failed`, 실패 채널과 원인을 함께 남깁니다.
- 알림 설정 API의 `effective_email_channel`은 자동 모드에서 실제 시도 가능한 채널 목록을 표시합니다.

## 실제 테스트 결과

- `notify-config`: 정상, `configured=true`
- `notify-test`: 실패 기록 정상
- 실제 `/lead` 접수: 저장 정상, 알림 실패 기록 정상
- 테스트 상담 삭제: 완료
- D1 보존 상담: 1건

## 운영 완료 조건

1. WordPress 운영 사이트에 `jauction-lead-mail-bridge` 플러그인을 실제 활성화합니다.
2. `/wp-json/jauction/v1/lead` 주소가 보안 플러그인의 `cupid.js` 보호 없이 Worker POST를 받을 수 있게 예외 처리합니다.
3. 위 주소가 올바른 토큰으로 `{"ok":true,"mail_sent":true}`를 반환하는지 확인합니다.
4. 또는 Cloudflare Email Sending에서 소유 도메인 발신 주소를 정상 활성화합니다.
5. 또는 Resend 같은 외부 메일 API 키를 Worker secret으로 넣고 `NOTIFY_PROVIDER=auto` 상태에서 재검증합니다.

## 결론

현재 운영상 가장 중요한 상담 저장은 정상입니다. 다만 직접 메일 발송은 아직 외부 발송 채널이 막혀 있어 완료가 아니며, 지금 배포된 Worker는 실패를 성공으로 숨기지 않고 원인을 남기도록 보완된 상태입니다.
