import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const workspace = path.resolve(__dirname, "..");
const root = fs.existsSync(path.join(workspace, "public", "index.html")) && !fs.existsSync(path.join(workspace, "index.html"))
  ? path.join(workspace, "public")
  : workspace;
const verification = readVerification();

const requiredFiles = [
  "index.html",
  "404.html",
  "faq/index.html",
  "privacy/index.html",
  "services/share-purchase/index.html",
  "services/share-auction/index.html",
  "services/inherited-share/index.html",
  "services/land-share/index.html",
  "services/co-ownership-dispute/index.html",
  "services/commercial-share/index.html",
  "assets/styles.css",
  "assets/main.js",
  "assets/hero-consultation.png",
  "favicon.svg",
  "robots.txt",
  "sitemap.xml",
  ".nojekyll",
];

const banned = [
  "FactoryPro",
  "factorypro",
  "Astra",
  "REPLACE_ME",
  "\uFFFD",
];

const requiredText = {
  "index.html": [
    "privacy_agree",
    "company_website",
    "https://jauction-lead-api.jiggyj.workers.dev/lead",
    "FAQPage",
    "ProfessionalService",
  ],
  "assets/main.js": ["localStorage", "jauction_last_submit", "sms:01068991601"],
  "robots.txt": ["Sitemap: https://jiggyj744-ctrl.github.io/sitemap.xml"],
  "sitemap.xml": [
    "https://jiggyj744-ctrl.github.io/",
    "https://jiggyj744-ctrl.github.io/services/share-purchase/",
    "https://jiggyj744-ctrl.github.io/services/share-auction/",
    "2026-06-30",
  ],
};

const errors = [];

for (const file of requiredFiles) {
  if (!fs.existsSync(path.join(root, file))) {
    errors.push(`missing required file: ${file}`);
  }
}

for (const [file, needles] of Object.entries(requiredText)) {
  if (!fs.existsSync(path.join(root, file))) continue;
  const content = read(file);
  for (const needle of needles) {
    if (!content.includes(needle)) {
      errors.push(`${file} missing text: ${needle}`);
    }
  }
}

const textFiles = [];
walk(root);

for (const file of textFiles) {
  const rel = path.relative(root, file).replaceAll("\\", "/");
  const content = fs.readFileSync(file, "utf8");
  for (const needle of banned) {
    if (content.includes(needle)) {
      errors.push(`${rel} contains banned text: ${needle}`);
    }
  }
  if (!verification.googleMeta && content.includes("google-site-verification")) {
    errors.push(`${rel} contains unmanaged google verification text`);
  }
  if (!verification.naverMeta && content.includes("naver-site-verification")) {
    errors.push(`${rel} contains unmanaged naver verification text`);
  }
}

const htmlFiles = textFiles.filter((file) => file.endsWith(".html"));
for (const file of htmlFiles) {
  const rel = path.relative(root, file).replaceAll("\\", "/");
  const content = fs.readFileSync(file, "utf8");
  if (!content.includes('<html lang="ko">')) errors.push(`${rel} missing lang=ko`);
  if (!content.includes('<meta name="description"')) errors.push(`${rel} missing description`);
  if (!content.includes('<link rel="canonical"')) errors.push(`${rel} missing canonical`);
  if (!content.includes('<link rel="icon"')) errors.push(`${rel} missing favicon`);
  if (!content.includes("/assets/styles.css?v=20260630")) errors.push(`${rel} missing stylesheet`);
  if (!content.includes("/assets/main.js?v=20260630")) errors.push(`${rel} missing script`);
}

if (verification.googleFile?.name) {
  assertVerificationFile(verification.googleFile);
}
if (verification.naverFile?.name) {
  assertVerificationFile(verification.naverFile);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log(`verification passed: ${requiredFiles.length} required files, ${htmlFiles.length} html files`);

function read(file) {
  return fs.readFileSync(path.join(root, file), "utf8");
}

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === ".git" || entry.name === ".wrangler" || entry.name === "tools") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full);
    } else if (/\.(html|css|js|xml|txt|md|mjs|json)$/i.test(entry.name)) {
      textFiles.push(full);
    }
  }
}

function readVerification() {
  const file = path.join(workspace, "tools", "search-verification.json");
  if (!fs.existsSync(file)) return {};
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return {};
  }
}

function assertVerificationFile(record) {
  const safeName = path.basename(record.name);
  if (safeName !== record.name || !/^[a-z0-9._-]+\.html$/i.test(safeName)) {
    errors.push(`invalid verification file name: ${record.name}`);
    return;
  }
  const target = path.join(root, safeName);
  if (!fs.existsSync(target)) {
    errors.push(`missing verification file: ${safeName}`);
    return;
  }
  if (record.content && fs.readFileSync(target, "utf8").trim() !== String(record.content).trim()) {
    errors.push(`verification file content mismatch: ${safeName}`);
  }
}
