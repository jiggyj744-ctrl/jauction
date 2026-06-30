if (window.lucide) {
  window.lucide.createIcons();
}

document.querySelectorAll('input[name="sal_submitted_at"]').forEach((input) => {
  input.value = Math.floor(Date.now() / 1000).toString();
});

document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", (event) => {
    const id = anchor.getAttribute("href");
    const target = id && document.querySelector(id);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
