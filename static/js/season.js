/* Zoo Planeta — seasonal effect over the top of every page (header + first section).
   Loaded only while SiteSettings has an active season. "snow": falling flakes; the pointer leaves paw prints
   in the snow that slowly get covered. Off with reduced motion; pauses when out of view. No dependencies. */
(function () {
  "use strict";
  const script = document.currentScript;
  if (!script || script.dataset.effect !== "snow") return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const canvas = document.createElement("canvas");
  canvas.className = "season-canvas";
  canvas.setAttribute("aria-hidden", "true");
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");

  // paw print: the same shapes as the #i-paw icon (viewBox 100×100)
  const pad = new Path2D("M50 50c-11 0-24 15-24 25 0 8 6 11 12 11 5 0 8-3 12-3s7 3 12 3c6 0 12-3 12-11 0-10-13-25-24-25z");
  const toes = [[22, 42, 8, 10, -20], [38, 24, 8, 11, -8], [62, 24, 8, 11, 8], [78, 42, 8, 10, 20]];

  const PRINT_LIFE = 5000;   // ms until a print is snowed over
  const MAX_PRINTS = 60;
  let w = 0, h = 0, dpr = 1, flakes = [], prints = [], visible = true, raf = 0, last = 0;

  const dark = () => document.body.dataset.heroTone === "dark" && window.scrollY < h;

  function areaHeight() {
    // header + the first block of the page, within sensible limits
    const first = document.querySelector("main > *");
    const bottom = first ? first.getBoundingClientRect().bottom + window.scrollY : 420;
    return Math.max(320, Math.min(bottom, 900));
  }

  function newFlake(top) {
    return {
      x: Math.random() * w,
      y: top ? -10 - Math.random() * 40 : Math.random() * h,
      r: 1.4 + Math.random() * 2.2,
      vy: 22 + Math.random() * 38,            // px per second
      sway: 10 + Math.random() * 20,
      phase: Math.random() * Math.PI * 2,
      freq: .4 + Math.random() * .8,
      crystal: Math.random() < .35,           // six-armed flake, reads as snow on any background
      rot: Math.random() * Math.PI,
      spin: (Math.random() - .5) * .8,
    };
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = document.documentElement.clientWidth;
    h = areaHeight();
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.height = `${h}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.round(Math.max(18, Math.min(60, (w * h) / 16000)) * (w < 700 ? .5 : 1));
    while (flakes.length < count) flakes.push(newFlake(false));
    flakes.length = count;
  }

  function drawPrint(p, alpha, light) {
    const s = p.size / 100;
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(p.angle);
    ctx.scale(s, s);
    ctx.translate(-50, -55);
    ctx.fillStyle = light ? `rgba(255,255,255,${alpha * .7})` : `rgba(17,17,17,${alpha * .2})`;
    ctx.fill(pad);
    for (const [cx, cy, rx, ry, rot] of toes) {
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, rot * Math.PI / 180, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawCrystal(x, y, size, rot) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rot);
    ctx.beginPath();
    for (let k = 0; k < 3; k++) {
      const a = k * Math.PI / 3;
      ctx.moveTo(-Math.cos(a) * size, -Math.sin(a) * size);
      ctx.lineTo(Math.cos(a) * size, Math.sin(a) * size);
    }
    ctx.lineCap = "round";
    ctx.strokeStyle = "rgba(17,17,17,.14)";
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
  }

  function frame(now) {
    raf = 0;
    if (!visible) return;
    const dt = Math.min((now - (last || now)) / 1000, .05);
    last = now;
    ctx.clearRect(0, 0, w, h);
    const light = dark();

    prints = prints.filter((p) => now - p.born < PRINT_LIFE);
    for (const p of prints) drawPrint(p, 1 - (now - p.born) / PRINT_LIFE, light);

    for (const f of flakes) {
      f.y += f.vy * dt;
      f.phase += f.freq * dt;
      f.rot += f.spin * dt;
      if (f.y > h + 6) Object.assign(f, newFlake(true));
      const x = f.x + Math.sin(f.phase) * f.sway;
      const fade = Math.min(1, (h - f.y) / 80);   // melt near the bottom of the area
      if (fade <= 0) continue;
      ctx.globalAlpha = fade;
      if (f.crystal) { drawCrystal(x, f.y, f.r * 2.4, f.rot); continue; }
      ctx.beginPath();                              // faint ring so the flake shows on white too
      ctx.arc(x, f.y, f.r + .9, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(17,17,17,.12)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, f.y, f.r, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    raf = requestAnimationFrame(frame);
  }

  function start() { if (!raf && visible) { last = 0; raf = requestAnimationFrame(frame); } }

  // paw prints where the pointer walks (mouse moves, finger drags, taps)
  let lastStep = null, foot = 1;
  function step(x, y) {
    if (y > h) return;
    const size = w < 640 ? 16 : 20;
    let angle = 0, off = 0;                     // a tap leaves one upright print
    if (lastStep) {
      const dx = x - lastStep.x, dy = y - lastStep.y;
      if (Math.hypot(dx, dy) < size * 1.7) return;
      angle = Math.atan2(dy, dx) + Math.PI / 2;
      foot = -foot;
      off = foot * size * .4;
    }
    prints.push({ x: x + Math.cos(angle) * off, y: y + Math.sin(angle) * off, angle, size, born: performance.now() });
    if (prints.length > MAX_PRINTS) prints.shift();
    lastStep = { x, y };
    start();
  }
  const skip = (e) => e.target.closest && e.target.closest("[data-nf-scene]");   // the 404 cat has its own play
  document.addEventListener("pointermove", (e) => { if (skip(e)) lastStep = null; else step(e.pageX, e.pageY); }, { passive: true });
  document.addEventListener("pointerdown", (e) => { lastStep = null; if (!skip(e)) step(e.pageX, e.pageY); }, { passive: true });
  document.addEventListener("pointerleave", () => { lastStep = null; });

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) start(); }).observe(canvas);
  }
  let resizeTimer = null;
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(resize, 150); });
  window.addEventListener("load", resize);   // images may change the height of the first block
  resize();
  start();
})();
