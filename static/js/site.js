/* Zoo Planeta — header menu, hero slider and small interactive bits. No dependencies. */
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

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // "Give a paw" button: paw prints run across the screen, then a note links to the Give a Paw section
  if (document.body.hasAttribute("data-paws")) {
    let running = false;
    const runPaws = () => {
      if (running || reducedMotion) return;
      running = true;
      const w = window.innerWidth, h = window.innerHeight;
      const size = w < 640 ? 22 : 30;          // print size, px
      const stride = size * 1.9;               // distance between steps
      const ltr = Math.random() < .5;
      const y0 = h * (.3 + Math.random() * .4), amp = h * .08, phase = Math.random() * 6;
      const trail = document.createElement("div");
      trail.className = "paw-trail";
      trail.setAttribute("aria-hidden", "true");
      const steps = Math.ceil((w + 2 * size) / stride);
      for (let k = 0; k <= steps; k++) {
        const t = k * stride - size;
        const x = ltr ? t : w - t;
        const y = y0 + Math.sin(t / 260 + phase) * amp;
        const dy = Math.cos(t / 260 + phase) * amp / 260;     // slope of the path
        const angle = Math.atan2(dy, ltr ? 1 : -1) * 180 / Math.PI + 90;
        const side = k % 2 ? 1 : -1;                          // left / right foot
        const off = side * size * .45;
        const el = document.createElement("span");
        el.className = "paw-step";
        el.style.cssText = `width:${size}px;height:${size}px;left:${x - size / 2 + off * Math.cos(angle * Math.PI / 180)}px;` +
          `top:${y - size / 2 + off * Math.sin(angle * Math.PI / 180)}px;transform:rotate(${angle}deg);animation-delay:${k * 110}ms`;
        el.innerHTML = '<svg viewBox="0 0 100 100"><use href="#i-paw"/></svg>';
        trail.appendChild(el);
      }
      document.body.appendChild(trail);
      setTimeout(() => { trail.remove(); running = false; }, steps * 110 + 1600);
    };

    const fab = document.querySelector("[data-paw-fab]");
    const toast = document.querySelector("[data-paw-toast]");
    if (fab) {
      const btn = fab.querySelector("button");
      // first page of the visit: the paw waves once and says what it wants
      let greeted = false;
      try { greeted = !!sessionStorage.getItem("zp-paw-hi"); sessionStorage.setItem("zp-paw-hi", "1"); } catch (e) { /* private mode */ }
      if (!greeted) {
        setTimeout(() => {
          btn.classList.add("is-wave");
          fab.classList.add("show-tip");
          setTimeout(() => { fab.classList.remove("show-tip"); btn.classList.remove("is-wave"); }, 4000);
        }, 3000);
      }
      let toastTimer = null;
      btn.addEventListener("click", () => {
        fab.classList.remove("show-tip");
        btn.classList.remove("is-give");
        void btn.offsetWidth;                  // restart the "give" animation
        btn.classList.add("is-give");
        runPaws();
        if (!toast) return;
        toast.hidden = false;
        requestAnimationFrame(() => toast.classList.add("is-on"));
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => {
          toast.classList.remove("is-on");
          setTimeout(() => { if (!toast.classList.contains("is-on")) toast.hidden = true; }, 300);
        }, 6000);
      });
    }

    // hidden bonus: the Konami code
    const konami = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"];
    let pos = 0;
    document.addEventListener("keydown", (e) => {
      const key = /^Key[A-Z]$/.test(e.code) ? e.code.slice(3).toLowerCase() : e.key;  // layout-independent letters
      pos = key === konami[pos] ? pos + 1 : (key === konami[0] ? 1 : 0);
      if (pos === konami.length) { pos = 0; runPaws(); }
    });
  }

  // 404: stroke the cat (eyes close, it purrs), it watches the pointer and knocks the cup off the table
  const scene = document.querySelector("[data-nf-scene]");
  if (scene && !reducedMotion) {
    const svg = scene.querySelector("svg");
    const cat = scene.querySelector("[data-nf-cat]");
    const cup = scene.querySelector("[data-nf-cup]");
    const pupils = [...scene.querySelectorAll(".cat-pupil")];
    let stroke = 0, lastX = null, lastY = null, petTimer = null, lastPurr = 0;

    const purr = () => {
      // above the cat's head (viewBox ≈ 230…290, 60), a little off each time
      const r = scene.getBoundingClientRect(), box = svg.getBoundingClientRect(), k = box.width / 420;
      const el = document.createElement("span");
      el.className = "nf-purr";
      el.textContent = scene.dataset.purr || "mrr";
      el.style.left = `${box.left - r.left + (230 + Math.random() * 60) * k}px`;
      el.style.top = `${box.top - r.top + (50 + Math.random() * 20) * k}px`;
      el.setAttribute("aria-hidden", "true");
      scene.appendChild(el);
      setTimeout(() => el.remove(), 1400);
    };

    scene.addEventListener("pointermove", (e) => {
      // pupils follow the pointer (up to 3 units of the viewBox)
      const box = svg.getBoundingClientRect();
      const k = 420 / box.width;
      pupils.forEach((p) => {
        const px = box.left + (+p.getAttribute("cx")) / k, py = box.top + (+p.getAttribute("cy")) / k;
        const a = Math.atan2(e.clientY - py, e.clientX - px);
        p.style.transform = `translate(${Math.cos(a) * 3}px, ${Math.sin(a) * 3}px)`;
      });
      // stroking: enough pointer travel over the cat
      if (!cat.contains(e.target)) { lastX = null; return; }
      if (lastX !== null) stroke += Math.hypot(e.clientX - lastX, e.clientY - lastY);
      lastX = e.clientX; lastY = e.clientY;
      if (stroke > 90) {
        scene.classList.add("is-petted");
        const now = Date.now();
        if (now - lastPurr > 550) { lastPurr = now; purr(); }
        clearTimeout(petTimer);
        petTimer = setTimeout(() => { scene.classList.remove("is-petted"); stroke = 0; }, 1200);
      }
    });
    scene.addEventListener("pointerleave", () => { lastX = null; pupils.forEach((p) => { p.style.transform = ""; }); });

    let busy = false;
    cup.addEventListener("click", () => {
      if (busy) return;
      busy = true;
      scene.classList.add("is-swiping");
      setTimeout(() => { scene.classList.remove("is-swiping"); cup.classList.add("is-falling"); }, 230);
      setTimeout(() => { cup.classList.remove("is-falling"); cup.classList.add("is-back"); }, 2400);
      setTimeout(() => { cup.classList.remove("is-back"); busy = false; }, 2950);
    });
  }

  // hero slider
  document.querySelectorAll("[data-slider]").forEach((root) => {
    const slides = [...root.querySelectorAll(".slide")];
    const dots = [...root.querySelectorAll(".slider-dots button")];
    if (slides.length < 2) return;
        let i = 0, timer = null;
    const go = (n) => {
      i = (n + slides.length) % slides.length;
      slides.forEach((s, k) => { s.classList.toggle("is-active", k === i); s.setAttribute("aria-hidden", String(k !== i)); });
      dots.forEach((d, k) => d.classList.toggle("is-active", k === i));
      // the header over the hero takes the text colour of the current slide
      if (root.closest(".hero")) document.body.dataset.heroTone = slides[i].dataset.tone || "light";
    };
    const play = () => { if (!reducedMotion) { stop(); timer = setInterval(() => go(i + 1), 7000); } };
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
