import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const tokenPath = path.join(root, ".admin-token.local");
const endpoint = process.env.JAUCTION_LEAD_API || "https://jauction-lead-api.jiggyj.workers.dev";
const token = process.env.JAUCTION_ADMIN_TOKEN || readTokenFile();

const [command, ...args] = process.argv.slice(2);

if (!token) {
  fail("missing admin token. Set JAUCTION_ADMIN_TOKEN or create workers/lead-api/.admin-token.local");
}

if (!command || command === "help") {
  printHelp();
  process.exit(0);
}

if (command === "list") {
  const params = new URLSearchParams();
  const limit = readFlag(args, "--limit") || "25";
  const status = readFlag(args, "--status");
  const q = readFlag(args, "--q");
  params.set("limit", limit);
  if (status) params.set("status", status);
  if (q) params.set("q", q);
  const data = await api(`/admin/leads?${params.toString()}`);
  printTable(data.leads || []);
} else if (command === "show") {
  const id = requireArg(args, 0, "id");
  const data = await api(`/admin/leads/${encodeURIComponent(id)}`);
  console.log(JSON.stringify(data.lead, null, 2));
} else if (command === "update") {
  const id = requireArg(args, 0, "id");
  const status = requireArg(args, 1, "status");
  const note = args.slice(2).join(" ");
  const data = await api(`/admin/leads/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify({ review_status: status, admin_note: note }),
  });
  console.log(JSON.stringify(data, null, 2));
} else if (command === "export") {
  const params = new URLSearchParams();
  params.set("limit", readFlag(args, "--limit") || "100");
  const status = readFlag(args, "--status");
  if (status) params.set("status", status);
  const data = await api(`/admin/leads?${params.toString()}`);
  printCsv(data.leads || []);
} else {
  fail(`unknown command: ${command}`);
}

async function api(pathname, init = {}) {
  const response = await fetch(`${endpoint}${pathname}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      ...(init.headers || {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok || data.ok === false) {
    fail(`api error ${response.status}: ${JSON.stringify(data)}`);
  }
  return data;
}

function readTokenFile() {
  if (!fs.existsSync(tokenPath)) return "";
  return fs.readFileSync(tokenPath, "utf8").trim();
}

function readFlag(args, name) {
  const index = args.indexOf(name);
  if (index === -1) return "";
  return args[index + 1] || "";
}

function requireArg(args, index, name) {
  const value = args[index];
  if (!value) fail(`missing ${name}`);
  return value;
}

function printTable(leads) {
  if (!leads.length) {
    console.log("no leads");
    return;
  }
  const rows = leads.map((lead) => ({
    id: lead.id,
    created_at: lead.created_at,
    status: lead.review_status,
    name: lead.name,
    phone: lead.phone,
    type: lead.lead_type,
    address: lead.case_or_address || "",
  }));
  console.table(rows);
}

function printCsv(leads) {
  const headers = ["id", "created_at", "updated_at", "review_status", "name", "phone", "lead_type", "case_or_address", "share_ratio", "owners", "property_status", "admin_note", "source_url"];
  console.log(headers.join(","));
  for (const lead of leads) {
    console.log(headers.map((key) => csv(lead[key] ?? "")).join(","));
  }
}

function csv(value) {
  const text = String(value).replaceAll('"', '""');
  return /[",\n]/.test(text) ? `"${text}"` : text;
}

function printHelp() {
  console.log(`Usage:
  node workers/lead-api/scripts/leads.mjs list [--limit 25] [--status new] [--q keyword]
  node workers/lead-api/scripts/leads.mjs show <id>
  node workers/lead-api/scripts/leads.mjs update <id> <new|reviewing|contacted|offer|hold|closed|spam> [note]
  node workers/lead-api/scripts/leads.mjs export [--limit 100] [--status new]`);
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
