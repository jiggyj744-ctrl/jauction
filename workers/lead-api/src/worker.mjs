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

    if (url.pathname === "/admin" && request.method === "GET") {
      return html(adminPageHtml(), 200);
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
      grid-template-columns: minmax(180px, 1fr) auto auto;
      gap: 10px;
      align-items: center;
      width: min(760px, 100%);
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
        row("출처", lead.source_url || "-") +
        "</dl>" +
        "<div><strong>상담 내용</strong><p class='message'>" + esc(lead.message || "-") + "</p></div>" +
        "<label>처리 상태<select id='reviewStatus'>" + statusOptions + "</select></label>" +
        "<label>관리 메모<textarea id='adminNote'>" + esc(lead.admin_note || "") + "</textarea></label>" +
        "<button type='button' id='saveLead'>저장</button>";
      document.getElementById("saveLead").addEventListener("click", () => updateLead(lead.id));
    }

    function exportCsv() {
      const headers = ["id", "created_at", "review_status", "name", "phone", "lead_type", "case_or_address", "source_url"];
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

    function row(key, value) {
      return "<div><dt>" + esc(key) + "</dt><dd>" + esc(value) + "</dd></div>";
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
