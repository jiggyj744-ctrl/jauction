const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
};

const MAX_BODY_BYTES = 12_000;
const MAX_FIELD_LENGTH = 1500;
const ADMIN_STATUSES = new Set(["new", "reviewing", "contacted", "offer", "hold", "closed", "spam"]);

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

    if (url.pathname === "/lead" && request.method === "POST") {
      return handleLead(request, env, corsHeaders);
    }

    if (url.pathname === "/admin/leads" && request.method === "GET") {
      return handleAdminList(request, env, corsHeaders);
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

    return json({ ok: true, id: result.meta?.last_row_id || null, status: "received" }, 201, corsHeaders);
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
      source_url
    FROM leads
    ${whereSql}
    ORDER BY id DESC
    LIMIT ? OFFSET ?
  `).bind(...binds, limit, offset).all();

  return json({ ok: true, leads: results.results || [], limit, offset }, 200, corsHeaders);
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
      admin_note
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
