import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const siteUrl = "https://jauction-share-acquisition.pages.dev";
const brand = "Jauction 지분매입 상담센터";
const phone = "010-6899-1601";
const tel = "01068991601";
const buildDate = "2026-06-30";
const leadEndpoint = "https://jauction-lead-api.jiggyj.workers.dev/lead";
const verificationConfigPath = path.join(root, "tools", "search-verification.json");

const sourceHero = path.resolve(
  root,
  "..",
  "jauction-clean",
  "wordpress",
  "theme",
  "share-auction-landing",
  "assets",
  "hero-consultation.png",
);

const services = [
  {
    slug: "share-purchase",
    title: "공유물 지분 매입",
    short: "공유자 합의가 멈춘 지분을 매입 가능성부터 검토합니다.",
    h1: "공유물 지분을 팔고 싶다면 매입 가능성부터 확인하세요",
    desc: "아파트, 토지, 상가, 건물 등 공동명의 부동산 지분을 등기와 점유 상태 기준으로 검토해 직접 매입 또는 정리 방향을 제안합니다.",
    points: ["등기부 지분율과 공유자 구조 확인", "점유, 임대차, 권리관계 검토", "매입 가능 범위와 보류 사유 안내"],
  },
  {
    slug: "share-auction",
    title: "지분경매 낙찰 전후 검토",
    short: "입찰 전 리스크와 낙찰 후 정리 전략을 분리해 봅니다.",
    h1: "지분경매 사건은 낙찰가보다 정리 구조가 먼저입니다",
    desc: "사건번호, 매각물건명세서, 공유자 우선매수권, 점유 상태, 공유물분할 가능성을 종합해 입찰 전후 판단 기준을 정리합니다.",
    points: ["공유자 우선매수권 검토", "낙찰 후 협의 및 분할 가능성 확인", "권리관계와 점유 리스크 점검"],
  },
  {
    slug: "inherited-share",
    title: "상속 지분 정리",
    short: "상속으로 생긴 소액 지분과 가족 공동명의 문제를 검토합니다.",
    h1: "상속 지분은 오래 둘수록 협의 비용이 커질 수 있습니다",
    desc: "상속 지분, 미등기 정리, 가족 공동명의 부동산, 연락이 어려운 공유자가 있는 사건의 매입 가능성과 대안을 안내합니다.",
    points: ["상속 지분율과 등기 상태 확인", "가족 공유자 협의 가능성 분류", "매입, 공동매각, 보류 판단"],
  },
  {
    slug: "land-share",
    title: "토지 지분 매입",
    short: "맹지, 도로, 지목, 개발 제한까지 토지 특성을 반영합니다.",
    h1: "토지 지분은 지분율보다 이용 가능성과 접근성이 중요합니다",
    desc: "맹지, 도로 접면, 지목, 개발 제한, 분할 가능성, 주변 거래 흐름을 확인해 토지 지분 매입 가능성을 검토합니다.",
    points: ["도로와 접면 조건 확인", "지목, 용도지역, 개발 제한 검토", "분할 가능성과 실사용 가치 판단"],
  },
  {
    slug: "co-ownership-dispute",
    title: "공유자 갈등 및 공유물분할",
    short: "협의 지연, 점유 갈등, 공유물분할 가능성을 정리합니다.",
    h1: "공유자 갈등이 길어질수록 지분 정리 기준이 필요합니다",
    desc: "협의가 어려운 공유자 구조, 점유자 문제, 공동매각 가능성, 공유물분할 청구 가능성을 구분해 현실적인 정리 방향을 봅니다.",
    points: ["공유자 수와 연락 가능성 확인", "점유 및 사용수익 구조 점검", "분할, 공동매각, 매입 가능성 비교"],
  },
  {
    slug: "commercial-share",
    title: "상가·건물 지분 검토",
    short: "임대차, 수익성, 관리비, 권리관계까지 함께 검토합니다.",
    h1: "상가와 건물 지분은 임대차와 수익 구조가 핵심입니다",
    desc: "상가, 오피스, 건물 지분은 임대차, 보증금, 관리비, 수익 배분, 점유 상태가 매입 가능성에 큰 영향을 줍니다.",
    points: ["임대차와 보증금 구조 확인", "수익 배분과 관리비 부담 점검", "건축물대장과 권리관계 검토"],
  },
];

const faqItems = [
  ["공유자 동의 없이 제 지분만 팔 수 있나요?", "자기 지분 처분은 가능하지만 실제 매입 가능성과 가격은 지분율, 점유 상태, 권리관계, 공유자 수에 따라 달라집니다."],
  ["사건번호만 있어도 상담이 가능한가요?", "가능합니다. 법원명, 사건번호, 매각기일이나 물건번호가 있으면 1차 검토를 시작할 수 있습니다."],
  ["지분경매 낙찰 후에도 상담할 수 있나요?", "가능합니다. 낙찰 후에는 공유자 협의, 우선매수권 행사 여부, 공유물분할 가능성, 점유 리스크를 따로 봐야 합니다."],
  ["토지 지분도 매입 검토가 되나요?", "가능합니다. 다만 맹지, 도로, 지목, 용도지역, 분할 가능성에 따라 보류될 수 있습니다."],
  ["상담하면 반드시 매각해야 하나요?", "아닙니다. 먼저 매입 가능성, 예상 검토 범위, 보류 사유, 다른 정리 방법을 확인한 뒤 결정하면 됩니다."],
  ["검토에 필요한 자료는 무엇인가요?", "주소, 사건번호, 등기부등본, 지분율, 공유자 수, 현재 점유 상태가 있으면 정확도가 올라갑니다. 자료가 부족해도 1차 접수는 가능합니다."],
];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function write(file, content) {
  const target = path.join(root, file);
  ensureDir(path.dirname(target));
  fs.writeFileSync(target, `${content.trim()}\n`, "utf8");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function layout({ title, description, pathName = "/", body, extraSchema = "" }) {
  const canonical = `${siteUrl}${pathName === "/" ? "/" : pathName}`;
  return `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <meta name="description" content="${escapeHtml(description)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <link rel="canonical" href="${canonical}">
  <meta property="og:locale" content="ko_KR">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="${brand}">
  <meta property="og:title" content="${escapeHtml(title)}">
  <meta property="og:description" content="${escapeHtml(description)}">
  <meta property="og:url" content="${canonical}">
  <meta property="og:image" content="${siteUrl}/assets/hero-consultation.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="#173b35">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="preload" as="image" href="/assets/hero-consultation.png">
  <link rel="stylesheet" href="/assets/styles.css?v=20260630">
  <script type="application/ld+json">${JSON.stringify(localBusinessSchema())}</script>
  ${extraSchema}
</head>
<body>
  <a class="skip-link" href="#main">본문 바로가기</a>
  ${header()}
  <main id="main">${body}</main>
  ${footer()}
  <div class="mobile-cta" aria-label="빠른 상담">
    <a href="tel:${tel}"><i data-lucide="phone"></i><span>전화</span></a>
    <a href="/#consult"><i data-lucide="clipboard-check"></i><span>접수</span></a>
  </div>
  <script src="https://unpkg.com/lucide@0.468.0/dist/umd/lucide.min.js" defer></script>
  <script src="/assets/main.js?v=20260630" defer></script>
</body>
</html>`;
}

function header() {
  return `<header class="site-header">
    <a class="brand" href="/" aria-label="${brand} 홈">
      <span class="brand-mark">J</span>
      <span class="brand-text">Jauction 지분매입</span>
    </a>
    <nav class="primary-nav" aria-label="주요 메뉴">
      <a href="/#screening">검토 기준</a>
      <a href="/#services">서비스</a>
      <a href="/#process">진행 절차</a>
      <a href="/faq/">FAQ</a>
    </nav>
    <a class="header-call" href="tel:${tel}"><i data-lucide="phone"></i><span>${phone}</span></a>
  </header>`;
}

function footer() {
  return `<footer class="site-footer">
    <div>
      <strong>${brand}</strong>
      <p>공유물 지분 매입 가능성 검토와 상담 접수를 위한 정적 랜딩 사이트입니다. 구체적인 법률·세무 판단은 사건 자료 확인 후 별도 전문가 검토가 필요할 수 있습니다.</p>
    </div>
    <nav class="footer-links" aria-label="하단 메뉴">
      <a href="/privacy/">개인정보 처리방침</a>
      <a href="/faq/">FAQ</a>
      <a href="tel:${tel}">${phone}</a>
    </nav>
  </footer>`;
}

function localBusinessSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "ProfessionalService",
    name: brand,
    url: siteUrl,
    telephone: phone,
    areaServed: "KR",
    serviceType: ["공유물 지분 매입 상담", "지분경매 검토", "상속 지분 정리", "토지 지분 매입 검토"],
    image: `${siteUrl}/assets/hero-consultation.png`,
  };
}

function faqSchema(items = faqItems) {
  return `<script type="application/ld+json">${JSON.stringify({
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map(([q, a]) => ({
      "@type": "Question",
      name: q,
      acceptedAnswer: { "@type": "Answer", text: a },
    })),
  })}</script>`;
}

function serviceSchema(service, pathName) {
  return `<script type="application/ld+json">${JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Service",
    name: service.title,
    provider: { "@type": "ProfessionalService", name: brand, url: siteUrl },
    areaServed: "KR",
    url: `${siteUrl}${pathName}`,
    description: service.desc,
  })}</script>`;
}

function homePage() {
  const title = "지분경매·공유물 지분 매입 상담 | 공유지분 검토 후 매입";
  const description = "공유물 지분, 상속 지분, 토지 지분, 지분경매 사건을 검토해 매입 가능성과 보류 사유를 안내하는 지분매입 전문 랜딩입니다.";
  const serviceCards = services.map((item) => `<article class="service-card">
      <div class="card-icon"><i data-lucide="${iconFor(item.slug)}"></i></div>
      <h3>${item.title}</h3>
      <p>${item.short}</p>
      <a href="/services/${item.slug}/">자세히 보기</a>
    </article>`).join("");
  const faqHome = faqItems.slice(0, 5).map(([q, a]) => `<details><summary>${q}</summary><p>${a}</p></details>`).join("");
  const body = `
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">공유지분 매도 · 지분경매 · 상속지분 정리</p>
        <h1>팔기 어려운 공유물 지분, 검토 후 매입 가능성을 제안합니다</h1>
        <p class="lead">공유자 합의가 멈춘 아파트·토지·상가 지분, 상속으로 생긴 소액 지분, 지분경매 낙찰 전후 사건을 등기와 사건자료 기준으로 확인합니다.</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="#consult"><i data-lucide="file-search"></i><span>내 지분 검토 요청</span></a>
          <a class="btn btn-secondary" href="tel:${tel}"><i data-lucide="phone-call"></i><span>${phone}</span></a>
        </div>
        <dl class="trust-strip">
          <div><dt>검토 기준</dt><dd>등기부·사건자료·점유 상태</dd></div>
          <div><dt>대상 지분</dt><dd>아파트·토지·상가·건물</dd></div>
          <div><dt>진행 방식</dt><dd>자료 확인 후 매입 조건 제안</dd></div>
        </dl>
      </div>
    </section>

    <section class="band intro-band" id="screening">
      <div class="section-head">
        <p class="eyebrow">먼저 보는 기준</p>
        <h2>공유지분은 시세보다 정리 구조가 먼저입니다</h2>
        <p>같은 1/2 지분이라도 공유자 수, 점유자, 임대차, 도로, 분할 가능성에 따라 매입 가능성과 보류 사유가 달라집니다.</p>
      </div>
      <div class="metric-grid">
        <article><strong>01</strong><h3>지분율과 공유자 수</h3><p>매입 후 협의 가능성과 회수 기간을 좌우합니다.</p></article>
        <article><strong>02</strong><h3>점유·임대차 상태</h3><p>실제 사용 가능성과 비용 부담을 먼저 봅니다.</p></article>
        <article><strong>03</strong><h3>권리관계와 제한</h3><p>압류, 근저당, 유치권, 법정지상권 가능성을 확인합니다.</p></article>
        <article><strong>04</strong><h3>분할·공동매각 가능성</h3><p>공유물분할, 공동매각, 직접 매입 중 현실적인 방향을 나눕니다.</p></article>
      </div>
    </section>

    <section class="band service-band" id="services">
      <div class="section-head">
        <p class="eyebrow">상담 범위</p>
        <h2>매도하려는 지분의 유형에 맞춰 검토합니다</h2>
      </div>
      <div class="service-grid">${serviceCards}</div>
    </section>

    <section class="band form-band" id="consult">
      <div class="consult-layout">
        <div class="consult-copy">
          <p class="eyebrow">무료 1차 접수</p>
          <h2>주소나 사건번호만 있어도 검토를 시작할 수 있습니다</h2>
          <p>상담 요청이 들어오면 등기, 지분율, 공유자 수, 점유 상태, 경매 진행 여부를 확인해 매입 가능성·보류 사유·추가 자료를 안내합니다.</p>
          <ul class="check-list">
            <li><i data-lucide="check"></i><span>등기부·매각물건명세서 기준 검토</span></li>
            <li><i data-lucide="check"></i><span>공유자 우선매수권과 분할 가능성 분리</span></li>
            <li><i data-lucide="check"></i><span>매입 가능, 보류, 추가자료 필요 사유 안내</span></li>
          </ul>
        </div>
        ${leadForm()}
      </div>
    </section>

    <section class="band process-band" id="process">
      <div class="section-head">
        <p class="eyebrow">진행 절차</p>
        <h2>접수부터 매입 제안까지 다섯 단계로 정리합니다</h2>
      </div>
      <ol class="process-list">
        <li><strong>기본정보 접수</strong><span>주소, 사건번호, 지분율, 연락처 확인</span></li>
        <li><strong>공적자료 확인</strong><span>등기부, 경매자료, 건축물·토지 정보 검토</span></li>
        <li><strong>리스크 분류</strong><span>점유, 임대차, 공유자 수, 권리 제한 구분</span></li>
        <li><strong>정리 방향 제안</strong><span>직접 매입, 공동매각, 협의, 보류 사유 안내</span></li>
        <li><strong>조건 협의</strong><span>자료 보완, 일정, 계약 방식 협의</span></li>
      </ol>
    </section>

    <section class="band risk-band">
      <div class="section-head">
        <p class="eyebrow">보류될 수 있는 사유</p>
        <h2>매입 검토는 가능성과 리스크를 함께 확인합니다</h2>
      </div>
      <div class="risk-table" role="table" aria-label="지분 매입 검토 리스크">
        <div role="row"><strong>권리관계 복잡</strong><span>가압류, 근저당, 유치권, 법정지상권 등은 별도 확인이 필요합니다.</span></div>
        <div role="row"><strong>점유자 불명확</strong><span>실사용자, 임차인, 무단점유 여부가 불명확하면 회수 기간이 길어질 수 있습니다.</span></div>
        <div role="row"><strong>공유자 구조 복잡</strong><span>공유자 수가 많거나 연락이 어려우면 협의와 분할 가능성을 별도로 봅니다.</span></div>
        <div role="row"><strong>토지 이용 제한</strong><span>맹지, 도로 문제, 개발 제한, 분할 제한은 매입 가능성에 직접 영향을 줍니다.</span></div>
      </div>
    </section>

    <section class="band case-band">
      <div class="section-head">
        <p class="eyebrow">주요 유입 상황</p>
        <h2>이런 지분이면 먼저 문의해 볼 수 있습니다</h2>
      </div>
      <div class="case-grid">
        <article><h3>상속 아파트 1/6 지분</h3><p>가족 공동명의가 장기화된 경우 점유자, 공유자 수, 공동매각 가능성을 확인합니다.</p></article>
        <article><h3>맹지 토지 1/8 지분</h3><p>도로 접면, 지목, 개발 제한과 분할 가능성을 먼저 검토합니다.</p></article>
        <article><h3>지분경매 낙찰 전 사건</h3><p>우선매수권, 낙찰 후 협의 가능성, 공유물분할 전략을 사전에 확인합니다.</p></article>
        <article><h3>상가·건물 일부 지분</h3><p>임대차, 수익 배분, 관리비 부담, 권리관계를 함께 봅니다.</p></article>
      </div>
    </section>

    <section class="band faq-band">
      <div class="section-head">
        <p class="eyebrow">FAQ</p>
        <h2>자주 묻는 질문</h2>
      </div>
      <div class="faq-list">${faqHome}</div>
      <p class="center-link"><a href="/faq/">FAQ 전체 보기</a></p>
    </section>

    <section class="final-cta">
      <div>
        <p class="eyebrow">1차 검토 접수</p>
        <h2>지금 가진 지분이 매입 가능한지 먼저 확인하세요</h2>
      </div>
      <a class="btn btn-primary" href="#consult"><i data-lucide="clipboard-check"></i><span>상담 접수하기</span></a>
    </section>`;
  write("index.html", layout({ title, description, pathName: "/", body, extraSchema: faqSchema(faqItems.slice(0, 5)) }));
}

function iconFor(slug) {
  return {
    "share-purchase": "hand-coins",
    "share-auction": "gavel",
    "inherited-share": "landmark",
    "land-share": "land-plot",
    "co-ownership-dispute": "scale",
    "commercial-share": "building-2",
  }[slug] || "file-search";
}

function leadForm() {
  return `<form class="lead-form" data-lead-form data-endpoint="${leadEndpoint}">
          <input type="text" name="company_website" class="hp-field" tabindex="-1" autocomplete="off" aria-hidden="true">
          <input type="hidden" name="submitted_at" value="">
          <label>이름<input name="name" autocomplete="name" required></label>
          <label>연락처<input name="phone" autocomplete="tel" inputmode="tel" required></label>
          <label>상담 유형
            <select name="type" required>
              <option value="">선택</option>
              <option>공유물 지분 매도</option>
              <option>지분경매 낙찰 전후</option>
              <option>상속 지분 정리</option>
              <option>토지 지분</option>
              <option>상가·건물 지분</option>
              <option>공유자 갈등·분할</option>
            </select>
          </label>
          <label>주소 또는 사건번호<input name="case_or_address" placeholder="예: 서울 ○○구 / 2026타경0000"></label>
          <div class="form-row">
            <label>지분율<input name="share" placeholder="예: 1/2, 1/8, 모름"></label>
            <label>공유자 수<input name="owners" placeholder="예: 3명, 모름"></label>
          </div>
          <label>현재 상태
            <select name="status">
              <option>매도 검토 중</option>
              <option>협의 지연</option>
              <option>경매 진행 중</option>
              <option>낙찰 완료</option>
              <option>소송·조정 중</option>
              <option>모름</option>
            </select>
          </label>
          <label>상담 내용<textarea name="message" rows="4" placeholder="공유자 상황, 점유자, 매도 희망 여부, 궁금한 점을 적어주세요."></textarea></label>
          <label class="privacy-check"><input type="checkbox" name="privacy_agree" required><span>상담 접수와 회신을 위한 개인정보 수집·이용에 동의합니다.</span></label>
          <button class="btn btn-primary" type="submit"><i data-lucide="send"></i><span>검토 요청 정리하기</span></button>
          <div class="form-result" hidden></div>
          <p class="form-note">입력한 내용은 지분 매입 가능성 검토와 상담 회신 목적으로만 저장됩니다.</p>
        </form>`;
}

function servicePage(service) {
  const pathName = `/services/${service.slug}/`;
  const body = `
    <section class="sub-hero">
      <div>
        <p class="eyebrow">${service.title}</p>
        <h1>${service.h1}</h1>
        <p class="lead">${service.desc}</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="/#consult"><i data-lucide="file-search"></i><span>검토 요청하기</span></a>
          <a class="btn btn-secondary" href="tel:${tel}"><i data-lucide="phone"></i><span>${phone}</span></a>
        </div>
      </div>
    </section>
    <section class="band intro-band">
      <div class="section-head">
        <p class="eyebrow">검토 포인트</p>
        <h2>${service.title}에서 먼저 확인하는 것</h2>
      </div>
      <div class="metric-grid">${service.points.map((point, index) => `<article><strong>${String(index + 1).padStart(2, "0")}</strong><h3>${point}</h3><p>자료가 부족해도 주소나 사건번호부터 접수하면 필요한 추가 자료를 안내합니다.</p></article>`).join("")}</div>
    </section>
    <section class="band split-band">
      <div class="split-copy">
        <div>
          <p class="eyebrow">검토 결과</p>
          <h2>무조건 매입보다 가능·보류·추가확인으로 나눠 판단합니다</h2>
        </div>
        <p>공유지분은 일반 매매보다 권리관계와 회수 구조가 중요합니다. 1차 검토에서는 매입 가능성, 보류 사유, 추가 자료, 협의 가능성을 분리해 안내합니다.</p>
      </div>
    </section>
    <section class="band form-band">
      <div class="consult-layout">
        <div class="consult-copy">
          <p class="eyebrow">빠른 접수</p>
          <h2>${service.title} 자료를 남겨주세요</h2>
          <p>주소, 사건번호, 지분율, 공유자 수, 현재 상태를 남기면 검토 순서를 잡을 수 있습니다.</p>
        </div>
        ${leadForm()}
      </div>
    </section>`;
  write(`services/${service.slug}/index.html`, layout({
    title: `${service.title} | ${brand}`,
    description: service.desc,
    pathName,
    body,
    extraSchema: serviceSchema(service, pathName),
  }));
}

function faqPage() {
  const body = `
    <section class="sub-hero compact">
      <div>
        <p class="eyebrow">FAQ</p>
        <h1>공유지분 매입 상담 전 자주 묻는 질문</h1>
        <p class="lead">상담 가능 여부, 필요한 자료, 지분경매와 공유물분할 리스크를 미리 확인할 수 있습니다.</p>
      </div>
    </section>
    <section class="band faq-band">
      <div class="faq-list">${faqItems.map(([q, a]) => `<details open><summary>${q}</summary><p>${a}</p></details>`).join("")}</div>
    </section>
    <section class="final-cta">
      <div><p class="eyebrow">자료가 부족해도 시작 가능</p><h2>주소나 사건번호부터 접수하세요</h2></div>
      <a class="btn btn-primary" href="/#consult"><i data-lucide="clipboard-check"></i><span>상담 접수하기</span></a>
    </section>`;
  write("faq/index.html", layout({
    title: `FAQ | ${brand}`,
    description: "공유물 지분 매입, 지분경매, 상속 지분, 토지 지분 상담 전 자주 묻는 질문입니다.",
    pathName: "/faq/",
    body,
    extraSchema: faqSchema(faqItems),
  }));
}

function privacyPage() {
  const body = `
    <section class="sub-hero compact">
      <div>
        <p class="eyebrow">개인정보 처리방침</p>
        <h1>상담 접수 개인정보 처리 기준</h1>
        <p class="lead">상담 접수와 회신에 필요한 최소 정보만 확인하는 것을 기준으로 합니다.</p>
      </div>
    </section>
    <section class="band text-page">
      <article>
        <h2>수집 항목</h2>
        <p>이름, 연락처, 상담 유형, 주소 또는 사건번호, 지분율, 공유자 수, 상담 내용, 개인정보 동의 여부를 상담 회신 목적으로 확인할 수 있습니다.</p>
        <h2>이용 목적</h2>
        <p>공유지분 매입 가능성 검토, 추가 자료 안내, 상담 회신, 매입 조건 협의에 사용합니다.</p>
        <h2>보관 기준</h2>
        <p>GitHub Pages 정적 사이트 자체에는 서버 저장 기능이 없습니다. 추후 별도 접수 API를 연결하는 경우 보관 기간과 파기 기준을 이 페이지에 반영합니다.</p>
        <h2>문의</h2>
        <p>개인정보 관련 문의는 전화 <a href="tel:${tel}">${phone}</a>로 연락할 수 있습니다.</p>
      </article>
    </section>`;
  write("privacy/index.html", layout({
    title: `개인정보 처리방침 | ${brand}`,
    description: "Jauction 지분매입 상담센터의 상담 접수 개인정보 처리 기준입니다.",
    pathName: "/privacy/",
    body,
  }));
}

function notFoundPage() {
  const body = `
    <section class="sub-hero compact">
      <div>
        <p class="eyebrow">404</p>
        <h1>페이지를 찾을 수 없습니다</h1>
        <p class="lead">공유지분 매입 상담은 홈 화면에서 다시 접수할 수 있습니다.</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="/"><i data-lucide="home"></i><span>홈으로 이동</span></a>
          <a class="btn btn-secondary" href="tel:${tel}"><i data-lucide="phone"></i><span>${phone}</span></a>
        </div>
      </div>
    </section>`;
  write("404.html", layout({
    title: `페이지 없음 | ${brand}`,
    description: "요청한 페이지를 찾을 수 없습니다.",
    pathName: "/404.html",
    body,
  }));
}

function assets() {
  ensureDir(path.join(root, "assets"));
  if (fs.existsSync(sourceHero)) {
    fs.copyFileSync(sourceHero, path.join(root, "assets", "hero-consultation.png"));
  }
  write("assets/styles.css", css());
  write("assets/main.js", js());
  write("favicon.svg", faviconSvg());
  write(".nojekyll", "");
}

function faviconSvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#173b35"/>
  <path d="M34 14v23c0 8-5 13-13 13-3 0-6-1-8-2l3-8c1 1 3 1 5 1 3 0 5-2 5-6V14h8z" fill="#ffffff"/>
  <path d="M40 42h12v8H40z" fill="#b88746"/>
</svg>`;
}

function css() {
  return `
:root {
  --ink: #17201c;
  --muted: #5e6862;
  --line: #dfe5df;
  --paper: #ffffff;
  --soft: #f4f7f2;
  --deep: #173b35;
  --deep-2: #0e2d29;
  --accent: #b88746;
  --accent-dark: #7a5628;
  --blue-soft: #e9f0f4;
  --danger-soft: #f8eee9;
  --radius: 8px;
  --shadow: 0 18px 50px rgba(15, 45, 38, 0.14);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  font-family: "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", Arial, sans-serif;
  background: var(--paper);
  letter-spacing: 0;
}
a { color: inherit; }
.skip-link {
  position: fixed;
  left: 12px;
  top: 12px;
  z-index: 200;
  transform: translateY(-160%);
  padding: 10px 14px;
  color: white;
  background: var(--deep);
  border-radius: 8px;
}
.skip-link:focus { transform: translateY(0); }
.site-header {
  position: sticky;
  top: 0;
  z-index: 50;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 0 32px;
  background: rgba(255, 255, 255, 0.95);
  border-bottom: 1px solid rgba(223, 229, 223, 0.95);
  backdrop-filter: blur(14px);
}
.brand, .header-call, .primary-nav a, .btn, .service-card a, .center-link a, .footer-links a { text-decoration: none; }
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 900;
  white-space: nowrap;
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  color: white;
  background: var(--deep);
  border-radius: 7px;
}
.brand-text { overflow-wrap: normal; }
.primary-nav {
  display: flex;
  gap: 22px;
  font-size: 15px;
  color: var(--muted);
}
.primary-nav a:hover { color: var(--deep); }
.header-call {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 16px;
  color: white;
  background: var(--deep);
  border-radius: 8px;
  font-weight: 900;
  white-space: nowrap;
}
svg { flex: 0 0 auto; }
.header-call svg, .btn svg, .check-list svg, .mobile-cta svg { width: 18px; height: 18px; }
.hero {
  min-height: calc(78vh - 72px);
  display: grid;
  align-items: center;
  padding: 72px 32px 58px;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.97) 0%, rgba(255,255,255,0.89) 42%, rgba(255,255,255,0.48) 72%, rgba(255,255,255,0.32) 100%),
    url("/assets/hero-consultation.png") center / cover no-repeat;
}
.hero-copy, .sub-hero > div {
  width: min(1120px, 100%);
  margin: 0 auto;
}
.eyebrow {
  margin: 0 0 12px;
  color: var(--accent-dark);
  font-size: 14px;
  font-weight: 900;
}
h1, h2, h3, p { word-break: keep-all; overflow-wrap: break-word; }
h1 {
  max-width: 780px;
  margin: 0;
  font-size: 50px;
  line-height: 1.16;
  letter-spacing: 0;
}
.lead {
  max-width: 720px;
  margin: 22px 0 0;
  color: #2f3935;
  font-size: 20px;
  line-height: 1.68;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 32px;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  min-height: 50px;
  padding: 0 22px;
  border: 1px solid transparent;
  border-radius: 8px;
  font-weight: 900;
  cursor: pointer;
}
.btn-primary { color: white; background: var(--deep); }
.btn-primary:hover { background: var(--deep-2); }
.btn-secondary {
  color: var(--deep);
  background: rgba(255, 255, 255, 0.92);
  border-color: var(--deep);
}
.trust-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 42px 0 0;
}
.trust-strip div {
  min-width: 190px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.trust-strip dt {
  margin-bottom: 5px;
  color: var(--muted);
  font-size: 13px;
}
.trust-strip dd { margin: 0; font-weight: 900; }
.band { padding: 84px 32px; }
.band > *, .consult-layout, .final-cta, .site-footer {
  width: min(1120px, 100%);
  margin-left: auto;
  margin-right: auto;
}
.intro-band, .process-band, .faq-band { background: var(--soft); }
.service-band { background: white; }
.section-head {
  max-width: 760px;
  margin: 0 auto 34px;
  text-align: center;
}
.section-head h2, .consult-layout h2, .split-copy h2, .final-cta h2 {
  margin: 0;
  font-size: 34px;
  line-height: 1.28;
  letter-spacing: 0;
}
.section-head p:not(.eyebrow) {
  color: var(--muted);
  line-height: 1.75;
}
.metric-grid, .service-grid, .case-grid {
  display: grid;
  gap: 16px;
}
.metric-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.metric-grid article, .service-card, .case-grid article {
  padding: 24px;
  background: white;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.metric-grid strong {
  color: var(--accent-dark);
  font-weight: 900;
}
.metric-grid h3, .service-card h3, .case-grid h3 {
  margin: 14px 0 10px;
  font-size: 19px;
}
.metric-grid p, .service-card p, .case-grid p, .consult-layout p, .split-copy p, .site-footer p, .faq-list p, .text-page p {
  margin: 0;
  color: var(--muted);
  line-height: 1.75;
}
.service-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.service-card {
  min-height: 232px;
  display: flex;
  flex-direction: column;
}
.card-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  color: var(--deep);
  background: var(--blue-soft);
  border-radius: 8px;
}
.card-icon svg { width: 23px; height: 23px; }
.service-card a {
  margin-top: auto;
  padding-top: 18px;
  color: var(--deep);
  font-weight: 900;
}
.form-band { color: white; background: var(--deep); }
.consult-layout {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(360px, 1fr);
  gap: 42px;
  align-items: start;
}
.consult-copy .eyebrow { color: #dfb879; }
.consult-layout p { color: rgba(255, 255, 255, 0.78); }
.check-list {
  display: grid;
  gap: 12px;
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
}
.check-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.9);
}
.lead-form {
  display: grid;
  gap: 14px;
  padding: 24px;
  color: var(--ink);
  background: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
}
.lead-form label {
  display: grid;
  gap: 7px;
  font-size: 14px;
  font-weight: 900;
}
.lead-form input, .lead-form select, .lead-form textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 12px 13px;
  font: inherit;
  color: var(--ink);
  background: white;
}
.lead-form textarea { resize: vertical; }
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.hp-field {
  position: absolute;
  left: -9999px;
  width: 1px !important;
  height: 1px;
  opacity: 0;
}
.privacy-check {
  display: grid !important;
  grid-template-columns: 18px 1fr;
  align-items: start;
  gap: 9px !important;
  font-weight: 700 !important;
}
.privacy-check input { width: 18px; margin-top: 2px; }
.form-note {
  font-size: 13px;
}
.form-result {
  padding: 14px;
  color: var(--deep);
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 8px;
  line-height: 1.7;
}
.form-result a {
  display: inline-flex;
  margin-top: 10px;
  margin-right: 8px;
  padding: 9px 12px;
  color: white;
  background: var(--deep);
  border-radius: 7px;
  text-decoration: none;
  font-weight: 900;
}
.process-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  padding: 0;
  list-style: none;
  counter-reset: step;
}
.process-list li {
  min-height: 178px;
  padding: 22px;
  background: white;
  border: 1px solid var(--line);
  border-radius: 8px;
  counter-increment: step;
}
.process-list li::before {
  content: counter(step, decimal-leading-zero);
  display: block;
  margin-bottom: 28px;
  color: var(--accent-dark);
  font-weight: 900;
}
.process-list strong, .process-list span { display: block; }
.process-list span {
  margin-top: 10px;
  color: var(--muted);
  line-height: 1.6;
}
.risk-band { background: #fff; }
.risk-table {
  display: grid;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}
.risk-table div {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 20px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--line);
}
.risk-table div:last-child { border-bottom: 0; }
.risk-table strong { color: var(--deep); }
.risk-table span { color: var(--muted); line-height: 1.65; }
.case-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.split-band { color: white; background: var(--deep-2); }
.split-copy {
  display: grid;
  grid-template-columns: 0.9fr 1fr;
  gap: 50px;
  align-items: center;
}
.split-copy .eyebrow { color: #dfb879; }
.split-copy p { color: rgba(255, 255, 255, 0.78); font-size: 18px; }
.faq-list {
  display: grid;
  gap: 10px;
}
.faq-list details {
  background: white;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.faq-list summary {
  cursor: pointer;
  padding: 18px 20px;
  font-weight: 900;
}
.faq-list p { padding: 0 20px 20px; }
.center-link { margin: 24px 0 0; text-align: center; }
.center-link a { color: var(--deep); font-weight: 900; }
.final-cta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 56px 32px;
}
.sub-hero {
  padding: 92px 32px 74px;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.97), rgba(255,255,255,0.82), rgba(255,255,255,0.46)),
    url("/assets/hero-consultation.png") center / cover no-repeat;
}
.sub-hero.compact { padding-bottom: 64px; }
.text-page article {
  max-width: 860px;
  padding: 0;
}
.text-page h2 {
  margin: 30px 0 10px;
  font-size: 24px;
}
.site-footer {
  display: flex;
  justify-content: space-between;
  gap: 28px;
  padding: 42px 32px 96px;
  border-top: 1px solid var(--line);
}
.site-footer p {
  max-width: 680px;
  margin-top: 10px;
  font-size: 14px;
}
.footer-links {
  display: flex;
  gap: 16px;
  white-space: nowrap;
}
.mobile-cta { display: none; }
@media (max-width: 980px) {
  .primary-nav { display: none; }
  h1 { font-size: 40px; }
  .lead { font-size: 18px; }
  .metric-grid, .service-grid, .case-grid, .process-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .consult-layout, .split-copy { grid-template-columns: 1fr; }
}
@media (max-width: 680px) {
  .site-header {
    height: 64px;
    padding: 0 16px;
  }
  .brand-text { max-width: 178px; white-space: normal; line-height: 1.15; }
  .header-call span { display: none; }
  .hero {
    min-height: auto;
    padding: 54px 18px 42px;
    background:
      linear-gradient(180deg, rgba(255,255,255,0.94), rgba(255,255,255,0.84)),
      url("/assets/hero-consultation.png") 62% center / cover no-repeat;
  }
  .sub-hero { padding: 56px 18px 48px; }
  h1 { font-size: 31px; }
  .lead { font-size: 16px; }
  .btn { width: 100%; padding: 0 14px; }
  .trust-strip div { width: 100%; }
  .band { padding: 62px 18px; }
  .section-head h2, .consult-layout h2, .split-copy h2, .final-cta h2 { font-size: 27px; }
  .metric-grid, .service-grid, .case-grid, .process-list { grid-template-columns: 1fr; }
  .consult-layout { gap: 28px; }
  .lead-form { padding: 18px; }
  .form-row { grid-template-columns: 1fr; }
  .risk-table div {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .final-cta, .site-footer {
    flex-direction: column;
    align-items: flex-start;
  }
  .footer-links {
    flex-wrap: wrap;
    white-space: normal;
  }
  .mobile-cta {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 60;
    display: grid;
    grid-template-columns: 1fr 1fr;
    background: white;
    border-top: 1px solid var(--line);
  }
  .mobile-cta a {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    min-height: 58px;
    color: var(--deep);
    text-decoration: none;
    font-weight: 900;
  }
  .mobile-cta a:first-child {
    color: white;
    background: var(--deep);
  }
  body { padding-bottom: 58px; }
}
`;
}

function js() {
  return `
window.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    window.lucide.createIcons();
  }

  document.querySelectorAll('a[href^="#"], a[href^="/#"]').forEach((anchor) => {
    anchor.addEventListener("click", (event) => {
      const href = anchor.getAttribute("href");
      const hash = href && href.includes("#") ? href.slice(href.indexOf("#")) : href;
      if (!hash || hash === "#") return;
      const target = document.querySelector(hash);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  document.querySelectorAll("[data-lead-form]").forEach((form) => {
    const submittedAt = form.querySelector('input[name="submitted_at"]');
    if (submittedAt) {
      submittedAt.value = new Date().toISOString();
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const result = form.querySelector(".form-result");
      const data = Object.fromEntries(new FormData(form).entries());
      if (data.company_website) return;
      const last = Number(localStorage.getItem("jauction_last_submit") || "0");
      const now = Date.now();
      if (now - last < 60000) {
        showResult(result, "연속 접수는 1분 뒤 다시 시도해 주세요.");
        return;
      }
      localStorage.setItem("jauction_last_submit", String(now));
      const summary = buildSummary(data);
      const endpoint = form.dataset.endpoint || window.JAUCTION_LEAD_ENDPOINT || "";
      if (endpoint) {
        try {
          const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...data, submitted_at: new Date().toISOString(), source: location.href }),
          });
          if (response.ok) {
            showResult(result, "접수되었습니다. 담당자가 확인 후 연락드리겠습니다.");
            form.reset();
            return;
          }
        } catch (error) {
          // Fall through to SMS fallback below.
        }
      }
      const encoded = encodeURIComponent(summary);
      showResult(
        result,
        "접수 내용이 정리되었습니다. 아래 버튼으로 문자 전달 또는 전화 상담을 진행하세요.",
        [
          { label: "문자로 보내기", href: "sms:${tel}?&body=" + encoded },
          { label: "전화하기", href: "tel:${tel}" },
        ],
        summary,
      );
    });
  });
});

function buildSummary(data) {
  const rows = [
    ["이름", data.name],
    ["연락처", data.phone],
    ["상담유형", data.type],
    ["주소/사건번호", data.case_or_address],
    ["지분율", data.share],
    ["공유자 수", data.owners],
    ["현재 상태", data.status],
    ["상담 내용", data.message],
    ["페이지", location.href],
  ];
  return "Jauction 지분매입 상담 요청\\n" + rows.map(([key, value]) => key + ": " + (value || "-")).join("\\n");
}

function showResult(target, message, links = [], copyText = "") {
  if (!target) return;
  target.hidden = false;
  target.innerHTML = "";
  const p = document.createElement("p");
  p.textContent = message;
  target.appendChild(p);
  links.forEach((link) => {
    const a = document.createElement("a");
    a.href = link.href;
    a.textContent = link.label;
    target.appendChild(a);
  });
  if (copyText && navigator.clipboard) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-secondary";
    button.textContent = "내용 복사";
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(copyText);
      button.textContent = "복사 완료";
    });
    target.appendChild(button);
  }
}
`;
}

function seoFiles() {
  const urls = ["/", "/faq/", "/privacy/", ...services.map((item) => `/services/${item.slug}/`)];
  write("robots.txt", `
User-agent: *
Allow: /

Sitemap: ${siteUrl}/sitemap.xml
`);
  write("sitemap.xml", `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((url) => `  <url>
    <loc>${siteUrl}${url}</loc>
    <lastmod>${buildDate}</lastmod>
    <changefreq>${url === "/" ? "weekly" : "monthly"}</changefreq>
    <priority>${url === "/" ? "1.0" : "0.8"}</priority>
  </url>`).join("\n")}
</urlset>`);
}

function docs() {
  write("README.md", `
# Jauction 지분매입 공개 사이트

공개 주소는 \`${siteUrl}/\`입니다. 공유물 지분, 지분경매, 상속 지분, 토지 지분, 상가·건물 지분을 가진 사람이 상담을 남기도록 만든 정적 랜딩 사이트입니다.

## 운영 범위

- 메인 화면: 지분 매도 상담 유도
- 세부 화면: 공유물 지분 매입, 지분경매, 상속 지분, 토지 지분, 공유자 갈등, 상가·건물 지분
- 상담 접수: Cloudflare Worker와 D1에 저장
- 관리자 화면: \`https://jauction-lead-api.jiggyj.workers.dev/admin\`
- 검색 등록 자료: \`robots.txt\`, \`sitemap.xml\`

## 주요 파일

- \`index.html\`: 메인 화면
- \`services/*/index.html\`: 세부 상담 화면
- \`faq/index.html\`: 자주 묻는 질문
- \`privacy/index.html\`: 개인정보 안내
- \`assets/styles.css\`: 화면 스타일
- \`assets/main.js\`: 상담 접수 화면 동작
- \`workers/lead-api/\`: 상담 저장과 관리자 화면
- \`tools/verify_site.mjs\`: 로컬 파일 점검
- \`tools/verify_live.mjs\`: 공개 주소 점검

## 상담 관리

관리자 화면과 관리자 명령은 별도 열쇠로 보호합니다. 열쇠 파일은 \`workers/lead-api/.admin-token.local\`에만 두고 GitHub에는 올리지 않습니다.

\`\`\`powershell
node workers/lead-api/scripts/leads.mjs list
node workers/lead-api/scripts/leads.mjs show 1
node workers/lead-api/scripts/leads.mjs update 1 contacted "전화 상담 완료"
node workers/lead-api/scripts/leads.mjs export --limit 100
\`\`\`

## 상담 알림

새 상담이 저장되면 이메일 또는 외부 알림 주소로 보낼 수 있도록 준비되어 있습니다. 실제 발송은 Cloudflare에 아래 값이 설정된 뒤 작동합니다.

- 이메일: \`RESEND_API_KEY\`, \`NOTIFY_EMAIL_FROM\`, \`NOTIFY_EMAIL_TO\`
- 외부 알림 주소: \`NOTIFY_WEBHOOK_URL\`, 필요 시 \`NOTIFY_WEBHOOK_TOKEN\`

알림 설정이 없으면 상담은 정상 저장되고, 관리자 화면에는 \`not_configured\`로 표시됩니다.

## 점검

\`\`\`powershell
node tools/verify_site.mjs
node tools/verify_live.mjs
\`\`\`
`);
}

function cleanLegacyVerificationFiles() {
  const keep = new Set(
    [readSearchVerification().googleFile?.name, readSearchVerification().naverFile?.name]
      .filter(Boolean),
  );
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (!entry.isFile()) continue;
    const lower = entry.name.toLowerCase();
    if (keep.has(entry.name)) continue;
    if (
      lower.startsWith("google") && lower.endsWith(".html") ||
      lower.startsWith("naver") && lower.endsWith(".html")
    ) {
      fs.unlinkSync(path.join(root, entry.name));
    }
  }
}

function readSearchVerification() {
  if (!fs.existsSync(verificationConfigPath)) {
    return {};
  }
  try {
    return JSON.parse(fs.readFileSync(verificationConfigPath, "utf8"));
  } catch {
    return {};
  }
}

function applySearchVerification() {
  const config = readSearchVerification();
  const block = searchVerificationBlock(config);
  for (const file of findHtmlFiles(root)) {
    let content = fs.readFileSync(file, "utf8");
    content = content.replace(/\n?\s*<!-- search-verification:start -->[\s\S]*?<!-- search-verification:end -->\n?/g, "\n");
    if (block && content.includes("</head>")) {
      content = content.replace("</head>", `${block}\n</head>`);
    }
    fs.writeFileSync(file, content, "utf8");
  }
  writeVerificationFile(config.googleFile);
  writeVerificationFile(config.naverFile);
}

function searchVerificationBlock(config) {
  const lines = [];
  if (config.googleMeta) {
    lines.push(`<meta name="google-site-verification" content="${escapeHtml(config.googleMeta)}">`);
  }
  if (config.naverMeta) {
    lines.push(`<meta name="naver-site-verification" content="${escapeHtml(config.naverMeta)}">`);
  }
  if (!lines.length) return "";
  return [
    "  <!-- search-verification:start -->",
    ...lines.map((line) => `  ${line}`),
    "  <!-- search-verification:end -->",
  ].join("\n");
}

function writeVerificationFile(record) {
  if (!record?.name) return;
  const safeName = path.basename(record.name);
  if (safeName !== record.name || !/^[a-z0-9._-]+\.html$/i.test(safeName)) return;
  fs.writeFileSync(path.join(root, safeName), `${record.content || ""}\n`, "utf8");
}

function findHtmlFiles(dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === ".git" || entry.name === ".wrangler" || entry.name === "workers") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...findHtmlFiles(full));
    } else if (entry.name.endsWith(".html")) {
      files.push(full);
    }
  }
  return files;
}

cleanLegacyVerificationFiles();
assets();
homePage();
services.forEach(servicePage);
faqPage();
privacyPage();
notFoundPage();
seoFiles();
docs();
applySearchVerification();

console.log(`Built ${brand} static site at ${root}`);
