import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const workspace = path.resolve(__dirname, "..");
const root = fs.existsSync(path.join(workspace, "public", "index.html")) && !fs.existsSync(path.join(workspace, "index.html"))
  ? path.join(workspace, "public")
  : workspace;
const configPath = path.join(workspace, "tools", "search-verification.json");
const args = parseArgs(process.argv.slice(2));

const config = readConfig();
if (args.clear) {
  config.googleMeta = "";
  config.naverMeta = "";
  config.googleFile = { name: "", content: "" };
  config.naverFile = { name: "", content: "" };
}
if (args["google-meta"]) config.googleMeta = extractMetaContent(args["google-meta"], "google-site-verification");
if (args["naver-meta"]) config.naverMeta = extractMetaContent(args["naver-meta"], "naver-site-verification");
if (args["google-file"]) config.googleFile = parseFileArg(args["google-file"], args["google-file-content"]);
if (args["naver-file"]) config.naverFile = parseFileArg(args["naver-file"], args["naver-file-content"]);

writeConfig(config);
applyMetaTags(config);
applyVerificationFile(config.googleFile);
applyVerificationFile(config.naverFile);

console.log("search verification prepared");

function parseArgs(items) {
  const out = {};
  for (let i = 0; i < items.length; i += 1) {
    const item = items[i];
    if (!item.startsWith("--")) continue;
    const key = item.slice(2);
    const value = items[i + 1] && !items[i + 1].startsWith("--") ? items[++i] : "true";
    out[key] = value;
  }
  return out;
}

function readConfig() {
  if (!fs.existsSync(configPath)) {
    return emptyConfig();
  }
  return { ...emptyConfig(), ...JSON.parse(fs.readFileSync(configPath, "utf8")) };
}

function emptyConfig() {
  return {
    googleMeta: "",
    naverMeta: "",
    googleFile: { name: "", content: "" },
    naverFile: { name: "", content: "" },
  };
}

function writeConfig(config) {
  fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
}

function extractMetaContent(value, expectedName) {
  const text = String(value || "").trim();
  if (!text || text === "true") return "";
  const tagMatch = text.match(/<meta\s+[^>]*name=["']([^"']+)["'][^>]*content=["']([^"']+)["'][^>]*>/i);
  if (tagMatch) {
    if (tagMatch[1] !== expectedName) throw new Error(`wrong meta name: ${tagMatch[1]}`);
    return tagMatch[2].trim();
  }
  return text;
}

function parseFileArg(name, content) {
  const safeName = path.basename(String(name || "").trim());
  if (!safeName || safeName !== name || !/^[a-z0-9._-]+\.html$/i.test(safeName)) {
    throw new Error(`invalid verification file name: ${name}`);
  }
  return { name: safeName, content: String(content || "").trim() };
}

function applyMetaTags(config) {
  const htmlFiles = findHtmlFiles(root);
  const block = buildBlock(config);
  for (const file of htmlFiles) {
    const rel = path.relative(root, file).replaceAll("\\", "/");
    if (rel.startsWith("workers/")) continue;
    let content = fs.readFileSync(file, "utf8");
    content = content.replace(/\n?\s*<!-- search-verification:start -->[\s\S]*?<!-- search-verification:end -->\n?/g, "\n");
    if (block && content.includes("</head>")) {
      content = content.replace("</head>", `${block}\n</head>`);
    }
    fs.writeFileSync(file, content, "utf8");
  }
}

function buildBlock(config) {
  const lines = [];
  if (config.googleMeta) {
    lines.push(`<meta name="google-site-verification" content="${escapeAttr(config.googleMeta)}">`);
  }
  if (config.naverMeta) {
    lines.push(`<meta name="naver-site-verification" content="${escapeAttr(config.naverMeta)}">`);
  }
  if (!lines.length) return "";
  return [
    "  <!-- search-verification:start -->",
    ...lines.map((line) => `  ${line}`),
    "  <!-- search-verification:end -->",
  ].join("\n");
}

function applyVerificationFile(record) {
  if (!record?.name) return;
  fs.writeFileSync(path.join(root, record.name), `${record.content || ""}\n`, "utf8");
}

function findHtmlFiles(dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === ".git" || entry.name === ".wrangler") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...findHtmlFiles(full));
    } else if (entry.name.endsWith(".html")) {
      files.push(full);
    }
  }
  return files;
}

function escapeAttr(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll('"', "&quot;");
}
