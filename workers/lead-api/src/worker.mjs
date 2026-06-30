const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
};

const MAX_BODY_BYTES = 12_000;
const MAX_FIELD_LENGTH = 1500;
const ADMIN_STATUSES = new Set(["new", "reviewing", "contacted", "offer", "hold", "closed", "spam"]);
const NOTIFY_PROVIDERS = new Set(["auto", "wordpress", "cloudflare", "resend", "all"]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const corsHeaders = buildCorsHeaders(request, env);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    if (url.pathname === "/health" && request.method === "GET") {
      return json({ ok: true, service: "jauction-lead-api" }, 200, corsHeaders);
    }

    if (url.pathname === "/admin" && request.method === "GET") {
      return html(adminPageHtml(), 200);
    }

    if (url.pathname === "/lead" && request.method === "POST") {
      return handleLead(request, env, corsHeaders);
    }

    if (url.pathname === "/admin/leads" && request.method === "GET") {
      return handleAdminList(request, env, corsHeaders);
    }

    if (url.pathname === "/admin/notification-config" && request.method === "GET") {
      return handleNotificationConfig(request, env, corsHeaders);
    }

    if (url.pathname === "/admin/notification-test" && request.method === "POST") {
      return handleNotificationTest(request, env, corsHeaders);
    }

    const leadMatch = url.pathname.match(/^\/admin\/leads\/(\d+)$/);
    if (leadMatch && request.method === "GET") {
      return handleAdminShow(request, env, corsHeaders, Number(leadMatch[1]));
    }

    if (leadMatch && request.method === "PATCH") {
      return handleAdminUpdate(request, env, corsHeaders, Number(leadMatch[1]));
    }

    return json({ ok: false, error: "not_found" }, 404, corsHeaders);
  },
};

async function handleLead(request, env, corsHeaders) {
  try {
    const origin = request.headers.get("Origin") || "";
    if (!isAllowedOrigin(origin, env)) {
      return json({ ok: false, error: "origin_not_allowed" }, 403, corsHeaders);
    }

    const text = await request.text();
    if (new TextEncoder().encode(text).length > MAX_BODY_BYTES) {
      return json({ ok: false, error: "payload_too_large" }, 413, corsHeaders);
    }

    const payload = parseJson(text);
    if (!payload) {
      return json({ ok: false, error: "invalid_json" }, 400, corsHeaders);
    }

    if (clean(payload.company_website)) {
      return json({ ok: true, status: "accepted" }, 202, corsHeaders);
    }

    const lead = normalizeLead(payload);
    const validationError = validateLead(lead);
    if (validationError) {
      return json({ ok: false, error: validationError }, 400, corsHeaders);
    }

    const ipHash = await hashIp(request);
    const rateLimit = await checkRateLimit(env, ipHash);
    if (!rateLimit.ok) {
      return json({ ok: false, error: "rate_limited" }, 429, corsHeaders);
    }

    const createdAt = new Date().toISOString();
    const userAgent = truncate(request.headers.get("User-Agent") || "", 500);

    const result = await env.DB.prepare(`
      INSERT INTO leads (
        created_at,
        source_url,
        name,
        phone,
        lead_type,
        case_or_address,
        share_ratio,
        owners,
        property_status,
        message,
        privacy_agree,
        user_agent,
        ip_hash
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      createdAt,
      lead.source,
      lead.name,
      lead.phone,
      lead.type,
      lead.case_or_address,
      lead.share,
      lead.owners,
      lead.status,
      lead.message,
      lead.privacy_agree ? 1 : 0,
      userAgent,
      ipHash,
    ).run();

    const leadId = result.meta?.last_row_id || null;
    if (leadId) {
      const notification = await notifyLead(env, { ...lead, id: leadId, created_at: createdAt });
      await markNotification(env, leadId, notification);
    }

    return json({ ok: true, id: leadId, status: "received" }, 201, corsHeaders);
  } catch (error) {
    return json({ ok: false, error: "server_error" }, 500, corsHeaders);
  }
}

async function handleAdminList(request, env, corsHeaders) {
  const auth = await requireAdmin(request, env);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, corsHeaders);

  const url = new URL(request.url);
  const limit = clampInt(url.searchParams.get("limit"), 1, 100, 25);
  const offset = clampInt(url.searchParams.get("offset"), 0, 10_000, 0);
  const status = clean(url.searchParams.get("status"));
  const q = clean(url.searchParams.get("q"));

  const where = [];
  const binds = [];
  if (status) {
    if (!ADMIN_STATUSES.has(status)) return json({ ok: false, error: "invalid_status" }, 400, corsHeaders);
    where.push("review_status = ?");
    binds.push(status);
  }
  if (q) {
    where.push("(name LIKE ? OR phone LIKE ? OR lead_type LIKE ? OR case_or_address LIKE ?)");
    binds.push(`%${q}%`, `%${q}%`, `%${q}%`, `%${q}%`);
  }

  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";
  const results = await env.DB.prepare(`
    SELECT
      id,
      created_at,
      updated_at,
      name,
      phone,
      lead_type,
      case_or_address,
      share_ratio,
      owners,
      property_status,
      review_status,
      admin_note,
      notification_status,
      notification_channel,
      notified_at,
      notification_error,
      source_url
    FROM leads
    ${whereSql}
    ORDER BY id DESC
    LIMIT ? OFFSET ?
  `).bind(...binds, limit, offset).all();

  return json({ ok: true, leads: results.results || [], limit, offset }, 200, corsHeaders);
}

async function handleNotificationConfig(request, env, corsHeaders) {
  const auth = await requireAdmin(request, env);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, corsHeaders);
  return json({ ok: true, notification: notificationConfig(env) }, 200, corsHeaders);
}

async function handleNotificationTest(request, env, corsHeaders) {
  const auth = await requireAdmin(request, env);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, corsHeaders);

  const now = new Date().toISOString();
  const notification = await notifyLead(env, {
    id: "test",
    created_at: now,
    name: "알림 점검",
    phone: "0000000000",
    type: "테스트",
    case_or_address: "관리자 테스트",
    share: "-",
    owners: "-",
    status: "테스트",
    message: "상담 알림 발송 경로가 정상인지 확인하는 테스트입니다.",
    source: "admin-notification-test",
  });

  return json({ ok: true, notification }, 200, corsHeaders);
}

async function handleAdminShow(request, env, corsHeaders, id) {
  const auth = await requireAdmin(request, env);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, corsHeaders);

  const lead = await env.DB.prepare(`
    SELECT
      id,
      created_at,
      updated_at,
      source_url,
      name,
      phone,
      lead_type,
      case_or_address,
      share_ratio,
      owners,
      property_status,
      message,
      privacy_agree,
      review_status,
      admin_note,
      notification_status,
      notification_channel,
      notified_at,
      notification_error
    FROM leads
    WHERE id = ?
  `).bind(id).first();

  if (!lead) return json({ ok: false, error: "lead_not_found" }, 404, corsHeaders);
  return json({ ok: true, lead }, 200, corsHeaders);
}

async function handleAdminUpdate(request, env, corsHeaders, id) {
  const auth = await requireAdmin(request, env);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, corsHeaders);

  const text = await request.text();
  if (new TextEncoder().encode(text).length > MAX_BODY_BYTES) {
    return json({ ok: false, error: "payload_too_large" }, 413, corsHeaders);
  }

  const payload = parseJson(text);
  if (!payload) return json({ ok: false, error: "invalid_json" }, 400, corsHeaders);

  const reviewStatus = clean(payload.review_status);
  const adminNote = clean(payload.admin_note);
  if (!ADMIN_STATUSES.has(reviewStatus)) {
    return json({ ok: false, error: "invalid_status" }, 400, corsHeaders);
  }

  const updatedAt = new Date().toISOString();
  const result = await env.DB.prepare(`
    UPDATE leads
    SET review_status = ?, admin_note = ?, updated_at = ?
    WHERE id = ?
  `).bind(reviewStatus, adminNote, updatedAt, id).run();

  if (!result.meta?.changes) return json({ ok: false, error: "lead_not_found" }, 404, corsHeaders);
  return json({ ok: true, id, review_status: reviewStatus, updated_at: updatedAt }, 200, corsHeaders);
}

async function notifyLead(env, lead) {
  const attempts = [];
  const provider = normalizeNotifyProvider(env.NOTIFY_PROVIDER);
  const wordpressReady = isWordPressMailReady(env);
  const cloudflareReady = isCloudflareEmailReady(env);
  const resendReady = isResendEmailReady(env);

  if (provider === "auto") {
    return notifyLeadAuto(env, lead, { wordpressReady, cloudflareReady, resendReady });
  }

  if ((provider === "wordpress" || provider === "all") && wordpressReady) {
    attempts.push(sendWordPressMailNotification(env, lead));
  }
  if ((provider === "cloudflare" || provider === "all") && cloudflareReady) {
    attempts.push(sendCloudflareEmailNotification(env, lead));
  }
  if ((provider === "resend" || provider === "all") && resendReady) {
    attempts.push(sendResendEmailNotification(env, lead));
  }
  if (env.NOTIFY_WEBHOOK_URL) {
    attempts.push(sendWebhookNotification(env, lead));
  }

  if (!attempts.length) {
    return {
      status: "not_configured",
      channel: "",
      notified_at: "",
      error: notificationConfig(env).missing.join(","),
    };
  }

  const results = await Promise.all(attempts.map(runNotificationAttempt));

  return notificationSummary(results);
}

async function notifyLeadAuto(env, lead, readiness) {
  const attempts = [];
  const ordered = [];
  if (readiness.wordpressReady) ordered.push(() => sendWordPressMailNotification(env, lead));
  if (readiness.cloudflareReady) ordered.push(() => sendCloudflareEmailNotification(env, lead));
  if (readiness.resendReady) ordered.push(() => sendResendEmailNotification(env, lead));

  for (const attempt of ordered) {
    const result = await runNotificationAttempt(attempt());
    attempts.push(result);
    if (result.ok) break;
  }

  if (env.NOTIFY_WEBHOOK_URL) {
    attempts.push(await runNotificationAttempt(sendWebhookNotification(env, lead)));
  }

  if (!attempts.length) {
    return {
      status: "not_configured",
      channel: "",
      notified_at: "",
      error: notificationConfig(env).missing.join(","),
    };
  }

  return notificationSummary(attempts, { autoFallback: true });
}

async function runNotificationAttempt(attempt) {
  try {
    return await attempt;
  } catch (error) {
    return { ok: false, channel: "unknown", error: clean(error?.message || "notification_failed") };
  }
}

function notificationSummary(results, options = {}) {
  const failed = results.filter((item) => !item.ok);
  const succeeded = results.filter((item) => item.ok);
  return {
    status: options.autoFallback && succeeded.length ? "sent" : (failed.length ? (failed.length === results.length ? "failed" : "partial_failed") : "sent"),
    channel: results.map((item) => item.channel).filter(Boolean).join(","),
    notified_at: new Date().toISOString(),
    error: failed.map((item) => `${item.channel}:${item.error}`).join(" | "),
  };
}

async function sendWordPressMailNotification(env, lead) {
  try {
    const headers = {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${env.WORDPRESS_WEBHOOK_TOKEN}`,
      "X-Jauction-Token": env.WORDPRESS_WEBHOOK_TOKEN,
    };
    const { response, text } = await fetchWordPressWithChallenge(env.WORDPRESS_WEBHOOK_URL, {
      method: "POST",
      headers,
      body: JSON.stringify(leadNotificationPayload(lead)),
    });
    const data = parseJson(text);
    if (!response.ok) {
      return { ok: false, channel: "wordpress_wp_mail", error: wordpressResponseError(response, data, text) };
    }
    if (!data || data.ok !== true || data.mail_sent !== true) {
      return { ok: false, channel: "wordpress_wp_mail", error: wordpressResponseError(response, data, text) || "wordpress_unexpected_response" };
    }
  } catch (error) {
    return { ok: false, channel: "wordpress_wp_mail", error: clean(error?.message || "wordpress_notification_failed") };
  }
  return { ok: true, channel: "wordpress_wp_mail", error: "" };
}

async function fetchWordPressWithChallenge(url, init) {
  let currentUrl = url;
  const headers = new Headers(init.headers || {});
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const response = await fetchWithTimeout(currentUrl, { ...init, headers });
    const text = await response.text();
    const challenge = parseCupidChallenge(text);
    if (!challenge) return { response, text };
    let cookie = "";
    try {
      cookie = await decryptCupidCookie(challenge);
    } catch (error) {
      throw new Error(`wordpress_cupid_challenge_failed:${clean(error?.message || "decrypt_failed")}`);
    }
    headers.set("Cookie", withCookie(headers.get("Cookie"), `CUPID=${cookie}`));
    currentUrl = challenge.location || currentUrl;
  }
  throw new Error("wordpress_challenge_loop");
}

function parseCupidChallenge(text) {
  if (!text || !text.includes("slowAES.decrypt") || !text.includes("document.cookie=\"CUPID=\"")) return null;
  const key = text.match(/var a=toNumbers\("([a-f0-9]+)"\)/i)?.[1];
  const iv = text.match(/b=toNumbers\("([a-f0-9]+)"\)/i)?.[1];
  const cipher = text.match(/c=toNumbers\("([a-f0-9]+)"\)/i)?.[1];
  const location = text.match(/location\.href="([^"]+)"/i)?.[1] || "";
  if (!key || !iv || !cipher) return null;
  return { key, iv, cipher, location };
}

async function decryptCupidCookie(challenge) {
  throw new Error("wordpress_cupid_challenge_requires_browser_or_server_bypass");
}

function wordpressResponseError(response, data, text) {
  if (data?.code || data?.message || data?.error) {
    return clean([response.status, data.code, data.message, data.error].filter(Boolean).join(":")) || String(response.status);
  }
  const content = clean(text || "");
  if (content.startsWith("<html") || content.includes("<script")) return `wordpress_non_json_response:${response.status}`;
  return clean([response.status, content.slice(0, 300)].filter(Boolean).join(":")) || String(response.status);
}

function withCookie(existing, next) {
  const keep = String(existing || "").split(";").map((item) => item.trim()).filter((item) => item && !item.startsWith("CUPID="));
  keep.push(next);
  return keep.join("; ");
}

async function sendCloudflareEmailNotification(env, lead) {
  const message = {
    from: emailAddress(env.NOTIFY_EMAIL_FROM, env.NOTIFY_EMAIL_FROM_NAME || "Jauction 상담 접수"),
    to: splitList(env.NOTIFY_EMAIL_TO),
    subject: `[Jauction 상담] ${lead.type} / ${lead.name}`,
    text: notificationText(lead),
    headers: {
      "X-Jauction-Lead-Id": String(lead.id),
    },
  };
  if (env.NOTIFY_EMAIL_REPLY_TO) {
    message.replyTo = env.NOTIFY_EMAIL_REPLY_TO;
  }

  try {
    const result = await env.EMAIL.send(message);
    return { ok: true, channel: "cloudflare_email", message_id: result?.messageId || "", error: "" };
  } catch (error) {
    const code = clean(error?.code || "");
    const detail = clean(error?.message || "email_send_failed");
    return { ok: false, channel: "cloudflare_email", error: [code, detail].filter(Boolean).join(":") };
  }
}

async function sendResendEmailNotification(env, lead) {
  const response = await fetchWithTimeout("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: formatSender(env.NOTIFY_EMAIL_FROM, env.NOTIFY_EMAIL_FROM_NAME),
      to: splitList(env.NOTIFY_EMAIL_TO),
      subject: `[Jauction 상담] ${lead.type} / ${lead.name}`,
      text: notificationText(lead),
      reply_to: env.NOTIFY_EMAIL_REPLY_TO || undefined,
    }),
  });
  if (!response.ok) {
    return { ok: false, channel: "resend_email", error: clean(await response.text()) || String(response.status) };
  }
  return { ok: true, channel: "resend_email", error: "" };
}

async function sendWebhookNotification(env, lead) {
  const headers = { "Content-Type": "application/json" };
  if (env.NOTIFY_WEBHOOK_TOKEN) headers.Authorization = `Bearer ${env.NOTIFY_WEBHOOK_TOKEN}`;
  const response = await fetchWithTimeout(env.NOTIFY_WEBHOOK_URL, {
    method: "POST",
    headers,
    body: JSON.stringify(leadNotificationPayload(lead)),
  });
  if (!response.ok) {
    return { ok: false, channel: "webhook", error: clean(await response.text()) || String(response.status) };
  }
  return { ok: true, channel: "webhook", error: "" };
}

function leadNotificationPayload(lead) {
  return {
    event: "lead.created",
    id: lead.id,
    created_at: lead.created_at,
    name: lead.name,
    phone: lead.phone,
    type: lead.type,
    case_or_address: lead.case_or_address,
    share: lead.share,
    owners: lead.owners,
    status: lead.status,
    message: lead.message,
    source: lead.source,
  };
}

async function markNotification(env, id, notification) {
  try {
    await env.DB.prepare(`
      UPDATE leads
      SET notification_status = ?, notification_channel = ?, notified_at = ?, notification_error = ?
      WHERE id = ?
    `).bind(
      notification.status || "unknown",
      notification.channel || "",
      notification.notified_at || "",
      notification.error || "",
      id,
    ).run();
  } catch {
    // Older databases can still receive leads before the notification fields are added.
  }
}

async function fetchWithTimeout(url, init) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 7000);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

function notificationText(lead) {
  return [
    "Jauction 새 상담이 접수되었습니다.",
    "",
    `접수번호: ${lead.id}`,
    `접수시각: ${lead.created_at}`,
    `이름: ${lead.name}`,
    `연락처: ${lead.phone}`,
    `상담유형: ${lead.type}`,
    `주소/사건번호: ${lead.case_or_address || "-"}`,
    `지분율: ${lead.share || "-"}`,
    `공유자 수: ${lead.owners || "-"}`,
    `현재 상태: ${lead.status || "-"}`,
    `출처: ${lead.source || "-"}`,
    "",
    lead.message || "-",
  ].join("\n");
}

function splitList(value) {
  return String(value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

function normalizeNotifyProvider(value) {
  const provider = clean(value).toLowerCase() || "auto";
  return NOTIFY_PROVIDERS.has(provider) ? provider : "auto";
}

function isCloudflareEmailReady(env) {
  return Boolean(env.EMAIL && typeof env.EMAIL.send === "function" && env.NOTIFY_EMAIL_TO && env.NOTIFY_EMAIL_FROM);
}

function isResendEmailReady(env) {
  return Boolean(env.RESEND_API_KEY && env.NOTIFY_EMAIL_TO && env.NOTIFY_EMAIL_FROM);
}

function isWordPressMailReady(env) {
  return Boolean(env.WORDPRESS_WEBHOOK_URL && env.WORDPRESS_WEBHOOK_TOKEN);
}

function notificationConfig(env) {
  const provider = normalizeNotifyProvider(env.NOTIFY_PROVIDER);
  const wordpress = {
    url: Boolean(env.WORDPRESS_WEBHOOK_URL),
    token: Boolean(env.WORDPRESS_WEBHOOK_TOKEN),
    ready: isWordPressMailReady(env),
  };
  const cloudflare = {
    binding: Boolean(env.EMAIL && typeof env.EMAIL.send === "function"),
    from: Boolean(env.NOTIFY_EMAIL_FROM),
    to: Boolean(env.NOTIFY_EMAIL_TO),
    ready: isCloudflareEmailReady(env),
  };
  const resend = {
    api_key: Boolean(env.RESEND_API_KEY),
    from: Boolean(env.NOTIFY_EMAIL_FROM),
    to: Boolean(env.NOTIFY_EMAIL_TO),
    ready: isResendEmailReady(env),
  };
  const webhook = {
    url: Boolean(env.NOTIFY_WEBHOOK_URL),
    token: Boolean(env.NOTIFY_WEBHOOK_TOKEN),
    ready: Boolean(env.NOTIFY_WEBHOOK_URL),
  };
  const configured = wordpress.ready || cloudflare.ready || resend.ready || webhook.ready;
  const missing = [];
  if (provider === "wordpress") {
    if (!wordpress.url) missing.push("WORDPRESS_WEBHOOK_URL");
    if (!wordpress.token) missing.push("WORDPRESS_WEBHOOK_TOKEN");
  } else if (provider === "cloudflare") {
    if (!cloudflare.binding) missing.push("EMAIL_binding");
    if (!cloudflare.from) missing.push("NOTIFY_EMAIL_FROM");
    if (!cloudflare.to) missing.push("NOTIFY_EMAIL_TO");
  } else if (provider === "resend") {
    if (!resend.api_key) missing.push("RESEND_API_KEY");
    if (!resend.from) missing.push("NOTIFY_EMAIL_FROM");
    if (!resend.to) missing.push("NOTIFY_EMAIL_TO");
  } else if (!configured) {
    missing.push("notification_provider");
    if (!wordpress.url && !cloudflare.binding && !resend.api_key && !webhook.url) {
      missing.push("WORDPRESS_WEBHOOK_URL_or_EMAIL_binding_or_RESEND_API_KEY_or_NOTIFY_WEBHOOK_URL");
    }
    if (wordpress.url && !wordpress.token) missing.push("WORDPRESS_WEBHOOK_TOKEN");
    if ((cloudflare.binding || resend.api_key) && !cloudflare.from && !resend.from) missing.push("NOTIFY_EMAIL_FROM");
    if ((cloudflare.binding || resend.api_key) && !cloudflare.to && !resend.to) missing.push("NOTIFY_EMAIL_TO");
  }
  return {
    provider,
    configured,
    effective_email_channel: effectiveEmailChannel(provider, wordpress, cloudflare, resend, webhook),
    wordpress_mail: wordpress,
    cloudflare_email: cloudflare,
    resend_email: resend,
    webhook,
    missing: [...new Set(missing)],
  };
}

function effectiveEmailChannel(provider, wordpress, cloudflare, resend, webhook) {
  if (provider === "auto" || provider === "all") {
    const channels = [];
    if (wordpress.ready) channels.push("wordpress_wp_mail");
    if (cloudflare.ready) channels.push("cloudflare_email");
    if (resend.ready) channels.push("resend_email");
    if (webhook.ready) channels.push("webhook");
    return channels.join(",");
  }
  if (provider === "wordpress" && wordpress.ready) return "wordpress_wp_mail";
  if (provider === "cloudflare" && cloudflare.ready) return "cloudflare_email";
  if (provider === "resend" && resend.ready) return "resend_email";
  if (provider === "webhook" && webhook.ready) return "webhook";
  return "";
}

function emailAddress(email, name) {
  const value = clean(email);
  const label = clean(name);
  return label ? { email: value, name: label } : value;
}

function formatSender(email, name) {
  const value = clean(email);
  const label = clean(name);
  return label ? `${label} <${value}>` : value;
}

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function normalizeLead(payload) {
  return {
    name: clean(payload.name),
    phone: clean(payload.phone),
    type: clean(payload.type),
    case_or_address: clean(payload.case_or_address),
    share: clean(payload.share),
    owners: clean(payload.owners),
    status: clean(payload.status),
    message: clean(payload.message),
    privacy_agree: payload.privacy_agree === true || payload.privacy_agree === "on" || payload.privacy_agree === "true",
    source: clean(payload.source) || "unknown",
  };
}

function validateLead(lead) {
  if (!lead.name) return "name_required";
  if (!lead.phone) return "phone_required";
  if (!lead.type) return "type_required";
  if (!lead.privacy_agree) return "privacy_required";
  if (!/^[0-9+\-\s().]{8,30}$/.test(lead.phone)) return "phone_invalid";
  return "";
}

function clean(value) {
  return truncate(String(value || "").replace(/\s+/g, " ").trim(), MAX_FIELD_LENGTH);
}

function truncate(value, maxLength) {
  return value.length > maxLength ? value.slice(0, maxLength) : value;
}

async function hashIp(request) {
  const ip = request.headers.get("CF-Connecting-IP") || request.headers.get("X-Forwarded-For") || "unknown";
  const day = new Date().toISOString().slice(0, 10);
  const bytes = new TextEncoder().encode(`${day}:${ip}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function checkRateLimit(env, ipHash) {
  const limit = Number(env.MAX_LEADS_PER_IP_PER_HOUR || "5");
  const since = new Date(Date.now() - 60 * 60 * 1000).toISOString();
  const row = await env.DB.prepare(
    "SELECT COUNT(*) AS count FROM leads WHERE ip_hash = ? AND created_at >= ?",
  ).bind(ipHash, since).first();
  return { ok: Number(row?.count || 0) < limit };
}

async function requireAdmin(request, env) {
  const expected = String(env.ADMIN_TOKEN || "");
  if (!expected) return { ok: false, status: 503, error: "admin_not_configured" };

  const header = request.headers.get("Authorization") || "";
  const provided = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
  if (!provided) return { ok: false, status: 401, error: "admin_auth_required" };

  const matches = await safeEqual(provided, expected);
  if (!matches) return { ok: false, status: 403, error: "admin_auth_invalid" };
  return { ok: true };
}

async function safeEqual(a, b) {
  const aHash = await sha256(a);
  const bHash = await sha256(b);
  if (aHash.length !== bHash.length) return false;
  let diff = 0;
  for (let i = 0; i < aHash.length; i += 1) {
    diff |= aHash.charCodeAt(i) ^ bHash.charCodeAt(i);
  }
  return diff === 0;
}

async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function clampInt(value, min, max, fallback) {
  const number = Number.parseInt(value || "", 10);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function buildCorsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowOrigin = isAllowedOrigin(origin, env) ? origin : "null";
  return {
    ...JSON_HEADERS,
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "POST, PATCH, OPTIONS, GET",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function isAllowedOrigin(origin, env) {
  if (!origin) return true;
  const allowed = String(env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return allowed.includes(origin);
}

function json(body, status, headers) {
  return new Response(JSON.stringify(body), { status, headers });
}

function html(body, status) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'self'; img-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
      "X-Frame-Options": "DENY",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
    },
  });
}

function adminPageHtml() {
  return `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Jauction 리드 관리자</title>
  <style>
    :root {
      --ink: #17201c;
      --muted: #5e6862;
      --line: #dfe5df;
      --paper: #ffffff;
      --soft: #f4f7f2;
      --deep: #173b35;
      --accent: #b88746;
      --danger: #9f2f22;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", Arial, sans-serif;
      background: var(--soft);
      letter-spacing: 0;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 18px 24px;
      background: rgba(255,255,255,.96);
      border-bottom: 1px solid var(--line);
    }
    h1 {
      margin: 0;
      font-size: 22px;
      line-height: 1.25;
    }
    main {
      width: min(1180px, 100%);
      margin: 0 auto;
      padding: 24px;
    }
    .toolbar, .detail, .table-wrap {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .toolbar {
      display: grid;
      grid-template-columns: minmax(220px, 1fr) 160px 120px 120px;
      gap: 10px;
      padding: 14px;
      margin-bottom: 16px;
    }
    input, select, textarea, button {
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px 12px;
      font: inherit;
      background: white;
    }
    textarea { min-height: 90px; resize: vertical; }
    button {
      cursor: pointer;
      color: white;
      background: var(--deep);
      border-color: var(--deep);
      font-weight: 800;
    }
    button.secondary {
      color: var(--deep);
      background: white;
    }
    button.danger {
      background: var(--danger);
      border-color: var(--danger);
    }
    .token-row {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) auto auto auto auto;
      gap: 10px;
      align-items: center;
      width: min(980px, 100%);
    }
    .status {
      color: var(--muted);
      font-size: 14px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 16px;
      align-items: start;
    }
    .table-wrap { overflow: auto; }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 860px;
    }
    th, td {
      padding: 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }
    th {
      position: sticky;
      top: 0;
      background: #f8faf7;
      color: var(--muted);
      font-weight: 800;
    }
    tr:hover td { background: #fbfcfa; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 3px 8px;
      border-radius: 999px;
      background: #e9f0f4;
      font-size: 12px;
      font-weight: 800;
    }
    .detail {
      display: grid;
      gap: 12px;
      padding: 16px;
    }
    .detail h2 {
      margin: 0;
      font-size: 18px;
    }
    .kv {
      display: grid;
      gap: 8px;
      margin: 0;
    }
    .kv div {
      display: grid;
      grid-template-columns: 90px 1fr;
      gap: 10px;
      font-size: 14px;
    }
    .kv dt {
      color: var(--muted);
      font-weight: 800;
    }
    .kv dd {
      margin: 0;
      word-break: break-word;
    }
    .empty {
      padding: 40px 18px;
      text-align: center;
      color: var(--muted);
    }
    .message {
      white-space: pre-wrap;
      line-height: 1.7;
    }
    @media (max-width: 860px) {
      header { display: grid; }
      .token-row, .toolbar, .layout { grid-template-columns: 1fr; }
      main { padding: 14px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Jauction 리드 관리자</h1>
    <div class="token-row">
      <input id="token" type="password" placeholder="관리자 토큰" autocomplete="off">
      <button id="saveToken" type="button">토큰 저장</button>
      <button id="clearToken" class="secondary" type="button">지우기</button>
      <button id="notifyConfig" class="secondary" type="button">알림 점검</button>
      <button id="notifyTest" class="secondary" type="button">테스트 발송</button>
    </div>
  </header>
  <main>
    <section class="toolbar">
      <input id="q" placeholder="이름, 연락처, 주소 검색">
      <select id="statusFilter">
        <option value="">전체 상태</option>
        <option value="new">new</option>
        <option value="reviewing">reviewing</option>
        <option value="contacted">contacted</option>
        <option value="offer">offer</option>
        <option value="hold">hold</option>
        <option value="closed">closed</option>
        <option value="spam">spam</option>
      </select>
      <button id="load" type="button">조회</button>
      <button id="exportCsv" class="secondary" type="button">CSV</button>
    </section>
    <p id="status" class="status">토큰 입력 후 조회하세요.</p>
    <section class="layout">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>접수일</th>
              <th>상태</th>
              <th>이름</th>
              <th>연락처</th>
              <th>유형</th>
              <th>주소/사건</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="rows">
            <tr><td class="empty" colspan="8">조회 결과가 없습니다.</td></tr>
          </tbody>
        </table>
      </div>
      <aside class="detail" id="detail">
        <h2>상세</h2>
        <p class="status">리드를 선택하세요.</p>
      </aside>
    </section>
  </main>
  <script>
    const state = {
      token: sessionStorage.getItem("jauction_admin_token") || "",
      leads: [],
      selected: null,
    };
    const statuses = ["new", "reviewing", "contacted", "offer", "hold", "closed", "spam"];
    const tokenInput = document.getElementById("token");
    const rows = document.getElementById("rows");
    const detail = document.getElementById("detail");
    const statusText = document.getElementById("status");
    tokenInput.value = state.token;

    document.getElementById("saveToken").addEventListener("click", () => {
      state.token = tokenInput.value.trim();
      sessionStorage.setItem("jauction_admin_token", state.token);
      setStatus("토큰을 세션에 저장했습니다.");
    });
    document.getElementById("clearToken").addEventListener("click", () => {
      state.token = "";
      tokenInput.value = "";
      sessionStorage.removeItem("jauction_admin_token");
      setStatus("토큰을 지웠습니다.");
    });
    document.getElementById("load").addEventListener("click", loadLeads);
    document.getElementById("exportCsv").addEventListener("click", exportCsv);
    document.getElementById("notifyConfig").addEventListener("click", loadNotificationConfig);
    document.getElementById("notifyTest").addEventListener("click", sendNotificationTest);

    async function loadLeads() {
      const params = new URLSearchParams();
      params.set("limit", "100");
      const q = document.getElementById("q").value.trim();
      const status = document.getElementById("statusFilter").value;
      if (q) params.set("q", q);
      if (status) params.set("status", status);
      const data = await api("/admin/leads?" + params.toString());
      state.leads = data.leads || [];
      renderRows();
      setStatus(state.leads.length + "건 조회됨");
    }

    async function showLead(id) {
      const data = await api("/admin/leads/" + encodeURIComponent(id));
      state.selected = data.lead;
      renderDetail(data.lead);
    }

    async function updateLead(id) {
      const reviewStatus = document.getElementById("reviewStatus").value;
      const adminNote = document.getElementById("adminNote").value;
      await api("/admin/leads/" + encodeURIComponent(id), {
        method: "PATCH",
        body: JSON.stringify({ review_status: reviewStatus, admin_note: adminNote }),
      });
      setStatus("저장했습니다.");
      await showLead(id);
      await loadLeads();
    }

    async function api(path, init = {}) {
      const token = tokenInput.value.trim() || state.token;
      if (!token) throw setStatus("관리자 토큰이 필요합니다.", true);
      state.token = token;
      sessionStorage.setItem("jauction_admin_token", token);
      const response = await fetch(path, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + token,
          ...(init.headers || {}),
        },
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) {
        setStatus("오류: " + (data.error || response.status), true);
        throw new Error(data.error || String(response.status));
      }
      return data;
    }

    function renderRows() {
      rows.innerHTML = "";
      if (!state.leads.length) {
        rows.innerHTML = '<tr><td class="empty" colspan="8">조회 결과가 없습니다.</td></tr>';
        return;
      }
      for (const lead of state.leads) {
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" + esc(lead.id) + "</td>" +
          "<td>" + esc(formatDate(lead.created_at)) + "</td>" +
          "<td><span class='pill'>" + esc(lead.review_status) + "</span></td>" +
          "<td>" + esc(lead.name) + "</td>" +
          "<td>" + esc(lead.phone) + "</td>" +
          "<td>" + esc(lead.lead_type) + "</td>" +
          "<td>" + esc(lead.case_or_address || "") + "</td>" +
          "<td><button class='secondary' type='button' data-id='" + esc(lead.id) + "'>상세</button></td>";
        tr.querySelector("button").addEventListener("click", () => showLead(lead.id));
        rows.appendChild(tr);
      }
    }

    function renderDetail(lead) {
      const statusOptions = statuses.map((item) => "<option value='" + item + "'" + (item === lead.review_status ? " selected" : "") + ">" + item + "</option>").join("");
      detail.innerHTML =
        "<h2>#" + esc(lead.id) + " " + esc(lead.name) + "</h2>" +
        "<dl class='kv'>" +
        row("접수일", formatDate(lead.created_at)) +
        row("수정일", lead.updated_at ? formatDate(lead.updated_at) : "-") +
        row("연락처", lead.phone) +
        row("유형", lead.lead_type) +
        row("주소/사건", lead.case_or_address || "-") +
        row("지분율", lead.share_ratio || "-") +
        row("공유자", lead.owners || "-") +
        row("상태", lead.property_status || "-") +
        row("알림", notificationLabel(lead)) +
        row("출처", lead.source_url || "-") +
        "</dl>" +
        "<div><strong>상담 내용</strong><p class='message'>" + esc(lead.message || "-") + "</p></div>" +
        "<label>처리 상태<select id='reviewStatus'>" + statusOptions + "</select></label>" +
        "<label>관리 메모<textarea id='adminNote'>" + esc(lead.admin_note || "") + "</textarea></label>" +
        "<button type='button' id='saveLead'>저장</button>";
      document.getElementById("saveLead").addEventListener("click", () => updateLead(lead.id));
    }

    function exportCsv() {
      const headers = ["id", "created_at", "review_status", "notification_status", "notification_channel", "notified_at", "name", "phone", "lead_type", "case_or_address", "source_url"];
      const lines = [headers.join(",")];
      for (const lead of state.leads) {
        lines.push(headers.map((key) => csv(lead[key] || "")).join(","));
      }
      const blob = new Blob([lines.join("\\n")], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "jauction-leads.csv";
      a.click();
      URL.revokeObjectURL(url);
    }

    async function loadNotificationConfig() {
      const data = await api("/admin/notification-config");
      const item = data.notification || {};
      const parts = [
        "알림 설정",
        "provider=" + (item.provider || "-"),
        "configured=" + Boolean(item.configured),
        "wp=" + ((item.wordpress_mail && item.wordpress_mail.ready) ? "ready" : "off"),
        "email=" + (item.effective_email_channel || "-"),
        "missing=" + ((item.missing || []).join(",") || "-"),
      ];
      setStatus(parts.join(" / "), !item.configured);
    }

    async function sendNotificationTest() {
      const data = await api("/admin/notification-test", {
        method: "POST",
        body: JSON.stringify({}),
      });
      const item = data.notification || {};
      const message = [
        "테스트 알림",
        "status=" + (item.status || "-"),
        "channel=" + (item.channel || "-"),
        item.error ? "error=" + item.error : "",
      ].filter(Boolean).join(" / ");
      setStatus(message, item.status !== "sent");
    }

    function row(key, value) {
      return "<div><dt>" + esc(key) + "</dt><dd>" + esc(value) + "</dd></div>";
    }

    function notificationLabel(lead) {
      const parts = [lead.notification_status || "-", lead.notification_channel || "", lead.notified_at ? formatDate(lead.notified_at) : ""].filter(Boolean);
      if (lead.notification_error) parts.push(lead.notification_error);
      return parts.join(" / ");
    }

    function setStatus(message, isError = false) {
      statusText.textContent = message;
      statusText.style.color = isError ? "var(--danger)" : "var(--muted)";
      return new Error(message);
    }

    function formatDate(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
    }

    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      }[char]));
    }

    function csv(value) {
      const text = String(value).replaceAll('"', '""');
      return /[",\\n]/.test(text) ? '"' + text + '"' : text;
    }
  </script>
</body>
</html>`;
}
