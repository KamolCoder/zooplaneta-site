/* Zoo Planeta — header menu and hero slider. No dependencies. */
(function () {
  "use strict";

  // mobile menu
  const nav = document.getElementById("mnav");
  const openBtn = document.querySelector("[data-open-nav]");
  if (nav && openBtn) {
    const setOpen = (open) => {
      nav.classList.toggle("open", open);
      nav.setAttribute("aria-hidden", String(!open));
      openBtn.setAttribute("aria-expanded", String(open));
      document.body.style.overflow = open ? "hidden" : "";
      if (open) nav.querySelector("a, button")?.focus();
    };
    openBtn.addEventListener("click", () => setOpen(true));
    nav.querySelector("[data-close-nav]")?.addEventListener("click", () => { setOpen(false); openBtn.focus(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && nav.classList.contains("open")) setOpen(false); });
  }

  // hero slider
  document.querySelectorAll("[data-slider]").forEach((root) => {
    const slides = [...root.querySelectorAll(".slide")];
    const dots = [...root.querySelectorAll(".slider-dots button")];
    if (slides.length < 2) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let i = 0, timer = null;
    const go = (n) => {
      i = (n + slides.length) % slides.length;
      slides.forEach((s, k) => { s.classList.toggle("is-active", k === i); s.setAttribute("aria-hidden", String(k !== i)); });
      dots.forEach((d, k) => d.classList.toggle("is-active", k === i));
      // dots/arrows take the colour of the current slide's text
      root.querySelector(".slider-ui").style.color = getComputedStyle(slides[i]).color;
    };
    const play = () => { if (!reduced) { stop(); timer = setInterval(() => go(i + 1), 7000); } };
    const stop = () => { if (timer) clearInterval(timer); timer = null; };
    root.querySelector("[data-prev]")?.addEventListener("click", () => { go(i - 1); play(); });
    root.querySelector("[data-next]")?.addEventListener("click", () => { go(i + 1); play(); });
    dots.forEach((d, k) => d.addEventListener("click", () => { go(k); play(); }));
    root.addEventListener("mouseenter", stop);
    root.addEventListener("mouseleave", play);
    root.addEventListener("focusin", stop);
    let x0 = null;
    root.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; stop(); }, { passive: true });
    root.addEventListener("touchend", (e) => {
      if (x0 === null) return;
      const dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 40) go(i + (dx < 0 ? 1 : -1));
      x0 = null; play();
    });
    go(0); play();
  });
})();
