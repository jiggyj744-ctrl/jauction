if (window.lucide) {
  window.lucide.createIcons();
}

document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", (event) => {
    const id = anchor.getAttribute("href");
    const target = id && document.querySelector(id);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

document.querySelectorAll(".lead-form input, .lead-form textarea").forEach((field) => {
  field.addEventListener("blur", () => {
    if (field.value.trim()) {
      field.dataset.filled = "true";
    } else {
      delete field.dataset.filled;
    }
  });
});

document.querySelectorAll("[data-preview-form]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const success = form.querySelector(".form-success");
    if (success) {
      success.hidden = false;
    }
  });
});
