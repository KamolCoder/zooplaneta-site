/* Zoo Planeta — seasonal decoration over the top of every page (header + first block).
   Loaded only while an effect is active (SiteSettings → core/season.py). Effects:
     winter  — snow                                           newyear — snow + garland under the header + hat (CSS)
     spring  — apricot petals                                  navruz  — petals + ornament strip (CSS) + tulips
     summer  — dandelion fluff drifting up                     hayit   — twinkling stars + crescent (tap → paw prints)
     autumn  — falling leaves
   Particles move away from the pointer. Reduced motion: no particles, static decorations only.
   Pauses when out of view. No dependencies. */
(function () {
  "use strict";
  const script = document.currentScript;
  if (!script) return;
  const effect = script.dataset.effect;
  const CONF = {
    winter: { particle: "snow", density: 1 },
    newyear: { particle: "snow", density: 1, deco: "garland" },
    spring: { particle: "petal", density: .55 },
    navruz: { particle: "petal", density: .5, deco: "tulips" },
    summer: { particle: "fluff", density: .3 },
    autumn: { particle: "leaf", density: .35 },
    hayit: { particle: "star", density: .45, deco: "crescent" },
  }[effect];
  if (!CONF) return;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NS = "http://www.w3.org/2000/svg";
  const greeting = script.dataset.greeting || "";

  // header + the first block of the page, within sensible limits
  function areaHeight() {
    const first = document.querySelector("main > *");
    const bottom = first ? first.getBoundingClientRect().bottom + window.scrollY : 420;
    return Math.max(320, Math.min(bottom, 900));
  }

  // ── holiday greeting: once per visit ──────────────────────────────────────
  let toastTimer = null;
  function toast(text, ms) {
    if (!text) return;
    let el = document.querySelector("[data-season-toast]");
    if (!el) {
      el = document.createElement("div");
      el.className = "paw-toast season-toast";
      el.setAttribute("role", "status");
      el.dataset.seasonToast = "";
      document.body.appendChild(el);
    }
    el.textContent = text;
    el.hidden = false;
    requestAnimationFrame(() => el.classList.add("is-on"));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.classList.remove("is-on");
      setTimeout(() => { if (!el.classList.contains("is-on")) el.hidden = true; }, 300);
    }, ms);
  }
  if (greeting) {
    const key = `zp-greet-${effect}-${new Date().getFullYear()}`;
    let seen = true;
    try { seen = !!sessionStorage.getItem(key); sessionStorage.setItem(key, "1"); } catch (e) { seen = false; }
    if (!seen) setTimeout(() => toast(greeting, 5000), 1500);
  }

  // ── decorations ───────────────────────────────────────────────────────────
  const header = document.querySelector(".header");
  let tulips = [];

  function buildGarland() {
    if (!header) return;
    header.querySelector(".garland")?.remove();
    const w = header.clientWidth, span = w < 640 ? 90 : 130, n = Math.ceil(w / span), sag = 9;
    let d = "M0 4", bulbs = "";
    for (let i = 0; i < n; i++) {
      const x0 = i * span, x1 = x0 + span, cx = x0 + span / 2, cy = 4 + 2 * sag;
      d += ` Q${cx} ${cy} ${x1} 4`;
      [.25, .5, .75].forEach((t, k) => {
        const x = (1 - t) * (1 - t) * x0 + 2 * (1 - t) * t * cx + t * t * x1;
        const y = (1 - t) * (1 - t) * 4 + 2 * (1 - t) * t * cy + t * t * 4;
        const fill = (i * 3 + k) % 2 ? "#fff" : "#FDCC27";
        bulbs += `<g class="bulb" transform="translate(${x.toFixed(1)} ${y.toFixed(1)})" style="animation-delay:${(Math.random() * 2.4).toFixed(2)}s">` +
          `<rect x="-2.5" y="-1" width="5" height="4" rx="1" fill="#111"/>` +
          `<ellipse cx="0" cy="9" rx="4.5" ry="6.5" fill="${fill}" stroke="#111" stroke-width="1.5"/></g>`;
      });
    }
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "garland");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("width", w);
    svg.setAttribute("height", 34);
    svg.innerHTML = `<path d="${d}" fill="none" stroke="#111" stroke-width="1.5"/>${bulbs}`;
    svg.querySelectorAll(".bulb").forEach((b) => b.addEventListener("pointerenter", () => {
      b.classList.add("pop");
      setTimeout(() => b.classList.remove("pop"), 700);
    }));
    header.appendChild(svg);
  }

  function buildTulips() {
    document.querySelector(".tulips")?.remove();
    const w = document.documentElement.clientWidth, h = areaHeight();
    const box = document.createElement("div");
    box.className = "tulips";
    box.setAttribute("aria-hidden", "true");
    box.style.height = `${h}px`;
    const count = Math.max(3, Math.min(10, Math.floor(w / 160)));
    tulips = [];
    for (let i = 0; i < count; i++) {
      const th = 44 + Math.random() * 22, tw = th / 2;
      const x = (i + .5) * w / count + (Math.random() - .5) * 40 - tw / 2, y = h - th;
      const el = document.createElement("div");
      el.className = "tulip";
      el.style.cssText = `left:${x}px;top:${y}px;width:${tw}px;height:${th}px;animation-delay:${i * 120}ms`;
      el.innerHTML = '<svg viewBox="0 0 30 60">' +
        '<path d="M15 60V26" stroke="#17894E" stroke-width="2.5" fill="none"/>' +
        '<path d="M15 52c-10-3-12-12-12-17 7 2 11 8 12 13z" fill="#17894E"/>' +
        '<path class="bud" d="M8 14c0 9 3 14 7 14s7-5 7-14l-3.5 3L15 10l-3.5 7z" fill="#FDCC27" stroke="#111" stroke-width="1.5" stroke-linejoin="round"/>' +
        '<path class="bloom" d="M15 28C6 28 3 21 2 12l6 4 7-9 7 9 6-4c-1 9-4 16-13 16z" fill="#FDCC27" stroke="#111" stroke-width="1.5" stroke-linejoin="round"/>' +
        "</svg>";
      box.appendChild(el);
      tulips.push({ el, x, y, w: tw, h: th, timer: null });
    }
    document.body.appendChild(box);
  }
  function openTulips(px, py) {
    for (const t of tulips) {
      if (px > t.x - 12 && px < t.x + t.w + 12 && py > t.y - 12 && py < t.y + t.h) {
        t.el.classList.add("open");
        clearTimeout(t.timer);
        t.timer = setTimeout(() => t.el.classList.remove("open"), 3000);
      }
    }
  }

  function buildCrescent() {
    if (!header || header.querySelector(".crescent")) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "crescent";
    btn.setAttribute("aria-label", greeting || "Hayit");
    btn.innerHTML = '<svg viewBox="0 0 46 80" aria-hidden="true">' +
      '<path d="M29 0v29" stroke="#111" stroke-width="1.5"/>' +
      '<path d="M29 29a16 16 0 1 0 0 30 20 20 0 0 1 0-30z" fill="#fff" stroke="#111" stroke-width="1.8" stroke-linejoin="round"/>' +
      '<path d="M33 38q0 6 6 6-6 0-6 6 0-6-6-6 6 0 6-6z" fill="#FDCC27" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/>' +
      "</svg>";
    btn.addEventListener("click", () => { window.ZP?.paws(); toast(greeting, 4000); });
    header.appendChild(btn);
  }

  const decorate = () => {
    if (CONF.deco === "garland") buildGarland();
    if (CONF.deco === "tulips") buildTulips();
    if (CONF.deco === "crescent") buildCrescent();
  };
  decorate();

  // ── particles ─────────────────────────────────────────────────────────────
  if (reduced) {
    if (CONF.deco === "tulips") document.addEventListener("pointermove", (e) => openTulips(e.pageX, e.pageY), { passive: true });
    let t = null;
    window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(decorate, 150); });
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.className = "season-canvas";
  canvas.setAttribute("aria-hidden", "true");
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  const rnd = (a, b) => a + Math.random() * (b - a);
  const LEAF_COLORS = ["#FDCC27", "#F2B705", "#E0A100"];
  const rising = CONF.particle === "fluff";

  let w = 0, h = 0, dpr = 1, parts = [], visible = true, raf = 0, last = 0;

  function spawn(initial) {
    const p = { x: rnd(0, w), sway: rnd(8, 20), phase: rnd(0, 6.3), freq: rnd(.4, 1.2), rot: rnd(0, 6.3),
      spin: rnd(-.6, .6), ix: 0, iy: 0, dx: 0 };
    switch (CONF.particle) {
      case "snow": Object.assign(p, { size: rnd(1.4, 3.6), vy: rnd(22, 60), crystal: Math.random() < .35 }); break;
      case "petal": Object.assign(p, { size: rnd(3, 5.5), vy: rnd(18, 40), sway: rnd(25, 45), spin: rnd(-1.5, 1.5) }); break;
      case "leaf": Object.assign(p, { size: rnd(7, 11), vy: rnd(25, 50), sway: rnd(30, 60), spin: rnd(-2, 2),
        color: LEAF_COLORS[Math.floor(Math.random() * LEAF_COLORS.length)] }); break;
      case "fluff": Object.assign(p, { size: rnd(5.5, 9), vy: -rnd(10, 24), sway: rnd(15, 30), spin: rnd(-.3, .3) }); break;
      case "star": Object.assign(p, { size: rnd(3, 6.5), vy: rnd(3, 8), sway: 4, freq: rnd(.6, 1.6) }); break;
    }
    if (initial) p.y = rnd(0, h);
    else p.y = rising ? h + 20 : -20;
    return p;
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = document.documentElement.clientWidth;
    h = areaHeight();
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.height = `${h}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.max(6, Math.round(Math.max(18, Math.min(60, (w * h) / 16000)) * CONF.density * (w < 700 ? .5 : 1)));
    while (parts.length < count) parts.push(spawn(true));
    parts.length = count;
    decorate();
  }

  // white shape with a faint dark outline: shows on white, yellow and photos alike
  function outlined(path, lw) {
    ctx.strokeStyle = "rgba(17,17,17,.16)";
    ctx.lineWidth = lw + 1.6;
    ctx.stroke(path);
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = lw;
    ctx.stroke(path);
  }

  const draw = {
    snow(p, x) {
      if (p.crystal) {
        const s = p.size * 2.4, path = new Path2D();
        for (let k = 0; k < 3; k++) {
          const a = p.rot + k * Math.PI / 3;
          path.moveTo(x - Math.cos(a) * s, p.y - Math.sin(a) * s);
          path.lineTo(x + Math.cos(a) * s, p.y + Math.sin(a) * s);
        }
        ctx.lineCap = "round";
        outlined(path, 1.5);
        return;
      }
      ctx.beginPath();
      ctx.arc(x, p.y, p.size + .9, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(17,17,17,.12)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
    },
    petal(p, x) {
      ctx.save();
      ctx.translate(x, p.y);
      ctx.rotate(p.rot);
      ctx.scale(1, .35 + .65 * Math.abs(Math.cos(p.phase * 1.7)));   // flutter
      ctx.beginPath();
      ctx.ellipse(0, 0, p.size * 1.6, p.size, 0, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
      ctx.strokeStyle = "rgba(17,17,17,.18)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    },
    leaf(p, x) {
      const s = p.size;
      ctx.save();
      ctx.translate(x, p.y);
      ctx.rotate(p.rot);
      ctx.scale(.3 + .7 * Math.abs(Math.cos(p.phase * 1.3)), 1);      // turning over
      ctx.beginPath();
      ctx.moveTo(0, -s);
      ctx.quadraticCurveTo(s * .9, -s * .2, 0, s);
      ctx.quadraticCurveTo(-s * .9, -s * .2, 0, -s);
      ctx.fillStyle = p.color;
      ctx.fill();
      ctx.strokeStyle = "rgba(17,17,17,.6)";
      ctx.lineWidth = 1.1;
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, -s * .7);
      ctx.lineTo(0, s * 1.35);
      ctx.stroke();
      ctx.restore();
    },
    fluff(p, x) {
      const s = p.size, path = new Path2D();
      for (let k = 0; k < 9; k++) {
        const a = p.rot + k * Math.PI * 2 / 9 - Math.PI / 2;
        if (Math.sin(a) > .75) continue;                             // gap where the seed hangs
        path.moveTo(x, p.y);
        path.lineTo(x + Math.cos(a) * s, p.y + Math.sin(a) * s);
      }
      path.moveTo(x, p.y);
      path.lineTo(x - Math.sin(p.rot) * s * 1.5, p.y + Math.cos(p.rot) * s * 1.5);
      ctx.lineCap = "round";
      outlined(path, 1);
      ctx.beginPath();
      ctx.arc(x - Math.sin(p.rot) * s * 1.6, p.y + Math.cos(p.rot) * s * 1.6, 1.4, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(17,17,17,.45)";
      ctx.fill();
    },
    star(p, x) {
      const s = p.size, path = new Path2D();
      path.moveTo(x, p.y - s);
      path.quadraticCurveTo(x, p.y, x + s, p.y);
      path.quadraticCurveTo(x, p.y, x, p.y + s);
      path.quadraticCurveTo(x, p.y, x - s, p.y);
      path.quadraticCurveTo(x, p.y, x, p.y - s);
      ctx.globalAlpha *= .35 + .65 * Math.abs(Math.sin(p.phase * 2));  // twinkle
      ctx.fillStyle = "#fff";
      ctx.fill(path);
      ctx.strokeStyle = "rgba(17,17,17,.2)";
      ctx.lineWidth = 1.1;
      ctx.stroke(path);
    },
  }[CONF.particle];

  function frame(now) {
    raf = 0;
    if (!visible) return;
    const dt = Math.min((now - (last || now)) / 1000, .05);
    last = now;
    ctx.clearRect(0, 0, w, h);

    const decay = Math.exp(-2.5 * dt);
    for (const p of parts) {
      p.ix *= decay;
      p.iy *= decay;
      p.y += (p.vy + p.iy) * dt;
      p.x += p.ix * dt;
      p.phase += p.freq * dt;
      p.rot += p.spin * dt;
      if (p.x < -40) p.x += w + 80;
      else if (p.x > w + 40) p.x -= w + 80;
      if (rising ? p.y < -20 : p.y > h + 20) Object.assign(p, spawn(false));
      const x = p.x + Math.sin(p.phase) * p.sway;
      p.dx = x;
      // melt near the bottom of the area (fluff: fade in from the bottom, out at the top)
      const fade = rising ? Math.min(1, (h - p.y) / 60, p.y / 80) : Math.min(1, (h - p.y) / 80);
      if (fade <= 0) continue;
      ctx.globalAlpha = fade;
      draw(p, x);
    }
    ctx.globalAlpha = 1;
    raf = requestAnimationFrame(frame);
  }
  function start() { if (!raf && visible) { last = 0; raf = requestAnimationFrame(frame); } }

  // the pointer: pushes particles away, opens tulips
  let lastPX = null, lastPY = null;
  const R = 90;
  function push(x, y) {
    const mvx = lastPX === null ? 0 : x - lastPX, mvy = lastPY === null ? 0 : y - lastPY;
    lastPX = x; lastPY = y;
    for (const p of parts) {
      const ddx = p.dx - x, ddy = p.y - y, d = Math.hypot(ddx, ddy);
      if (d > R || d < .01) continue;
      const f = 1 - d / R;
      p.ix = Math.max(-500, Math.min(500, p.ix + ddx / d * f * 120 + mvx * f * 6));
      p.iy = Math.max(-500, Math.min(500, p.iy + ddy / d * f * 120 + mvy * f * 6));
    }
  }
  function pointer(x, y) {
    if (y > h) { lastPX = null; return; }
    push(x, y);
    if (CONF.deco === "tulips") openTulips(x, y);
    start();
  }
  const skip = (e) => e.target.closest && e.target.closest("[data-nf-scene]");   // the 404 cat has its own play
  document.addEventListener("pointermove", (e) => {
    if (skip(e)) lastPX = null; else pointer(e.pageX, e.pageY);
  }, { passive: true });
  document.addEventListener("pointerdown", (e) => {
    lastPX = null;
    if (!skip(e)) pointer(e.pageX, e.pageY);
  }, { passive: true });

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) start(); }).observe(canvas);
  }
  let resizeTimer = null;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(resize, 150); });
  window.addEventListener("load", resize);   // images may change the height of the first block
  resize();
  start();
})();
