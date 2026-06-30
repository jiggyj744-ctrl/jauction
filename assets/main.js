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
          { label: "문자로 보내기", href: "sms:01068991601?&body=" + encoded },
          { label: "전화하기", href: "tel:01068991601" },
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
  return "Jauction 지분매입 상담 요청\n" + rows.map(([key, value]) => key + ": " + (value || "-")).join("\n");
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
