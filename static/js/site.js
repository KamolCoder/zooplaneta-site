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

  // reveal sections as they scroll into view (CSS hides them only under html.js)
  const revealEls = document.querySelectorAll(".reveal, .reveal-group");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
    }), { rootMargin: "0px 0px -8% 0px" });
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-in"));
  }

  // "Get the app" buttons go straight to the right store on phones
  const ua = navigator.userAgent || "";
  const platform = /iPhone|iPad|iPod/.test(ua) ? "ios" : /Android/.test(ua) ? "android" : "";
  document.querySelectorAll("[data-app-link]").forEach((a) => {
    const url = platform && a.dataset[platform];
    if (url) { a.href = url; a.target = "_blank"; a.rel = "noopener"; }
  });

  // copy a promo code
  document.querySelectorAll("[data-copy]").forEach((btn) => btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(btn.dataset.copy);
      const label = btn.lastChild.textContent;
      btn.lastChild.textContent = btn.dataset.copied;
      setTimeout(() => { btn.lastChild.textContent = label; }, 1800);
    } catch (e) { /* clipboard blocked: the code is visible anyway */ }
  }));

  // home: transparent header over the hero until the page scrolls
  if (document.body.classList.contains("home-hero")) {
    const first = document.querySelector(".hero .slide");
    document.body.dataset.heroTone = first ? first.dataset.tone || "light" : "light";
    const header = document.querySelector(".header");
    const onScroll = () => header?.classList.toggle("is-scrolled", window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
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
      // the header over the hero takes the text colour of the current slide
      if (root.closest(".hero")) document.body.dataset.heroTone = slides[i].dataset.tone || "light";
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
