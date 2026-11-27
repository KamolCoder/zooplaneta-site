/* Store finder (list + map) and the single-store map. Needs Leaflet (loaded before, deferred). */
(function () {
  "use strict";
  const tiles = window.MAP_TILES || { url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", attribution: "&copy; OpenStreetMap" };
  const TASHKENT = [41.3111, 69.2797];

  function pinIcon(state) {
    const cls = "pin" + (state.selected ? " is-selected" : "") + (state.closed ? " is-closed" : "");
    return L.divIcon({
      className: "", iconSize: [30, 40], iconAnchor: [15, 40], popupAnchor: [0, -36],
      html: `<div class="${cls}"><svg viewBox="0 0 30 40"><path class="body" d="M15 0C6.7 0 0 6.6 0 14.8 0 25.9 15 40 15 40s15-14.1 15-25.2C30 6.6 23.3 0 15 0z"/><circle class="dot" cx="15" cy="15" r="6"/></svg></div>`,
    });
  }
  function baseMap(el, opts) {
    const map = L.map(el, Object.assign({ scrollWheelZoom: false }, opts || {})).setView(TASHKENT, 11);
    L.tileLayer(tiles.url, { maxZoom: 19, attribution: tiles.attribution }).addTo(map);
    map.on("focus click", () => map.scrollWheelZoom.enable());
    return map;
  }

  // single store page
  const single = document.getElementById("store-map");
  if (single && window.L) {
    const pos = [parseFloat(single.dataset.lat), parseFloat(single.dataset.lng)];
    const map = baseMap(single);
    map.setView(pos, 16);
    L.marker(pos, { icon: pinIcon({}), title: single.dataset.name }).addTo(map);
  }

  // overview maps (home page, "stores map" block): every store as a pin, created when scrolled into view
  document.querySelectorAll("[data-overview-map]").forEach((el) => {
    const stores = JSON.parse(document.getElementById(el.dataset.src).textContent);
    const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const init = () => {
      if (!window.L || el.dataset.ready) return;
      el.dataset.ready = "1";
      const map = baseMap(el);
      const pts = [];
      stores.forEach((s) => {
        if (s.lat == null || s.lng == null) return;
        L.marker([s.lat, s.lng], { icon: pinIcon({}), title: s.name, keyboard: true })
          .bindPopup(`<b>${esc(s.name)}</b>${esc(s.address)}<br><a href="${esc(s.url)}">${esc(el.dataset.more)}</a> · <a href="${esc(s.route)}" target="_blank" rel="noopener">${esc(el.dataset.route)}</a>`)
          .addTo(map);
        pts.push([s.lat, s.lng]);
      });
      if (pts.length > 1) map.fitBounds(pts, { padding: [32, 32] });
    };
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting)) { io.disconnect(); init(); }
      }, { rootMargin: "300px" });
      io.observe(el);
    } else {
      init();
    }
  });

  // finder
  const root = document.querySelector("[data-store-finder]");
  if (!root) return;
  const STORES = JSON.parse(document.getElementById("stores-data").textContent);
  const T = JSON.parse(document.getElementById("finder-i18n").textContent);
  const items = new Map([...root.querySelectorAll(".store-item")].map((el) => [+el.dataset.id, el]));
  const qInput = root.querySelector("[data-q]");
  const districtSel = root.querySelector("[data-district]");
  const citySel = root.querySelector("[data-city]");
  const openBtn = root.querySelector("[data-open]");
  const nearBtn = root.querySelector("[data-near]");
  const layout = root.querySelector(".store-layout");
  const list = root.querySelector("[data-list]");
  const emptyEl = root.querySelector("[data-empty]");
  const countEl = root.querySelector("[data-count]");
  let onlyOpen = false, userPos = null, selected = null, map = null, userMarker = null;
  const markers = new Map();

  const nowMinutes = () => {
    const p = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Tashkent", hour: "2-digit", minute: "2-digit", hour12: false }).formatToParts(new Date());
    return (+p.find((x) => x.type === "hour").value % 24) * 60 + +p.find((x) => x.type === "minute").value;
  };
  const mins = (s) => { const [h, m] = s.split(":").map(Number); return h * 60 + m; };
  const isOpen = (s) => {
    const o = mins(s.opens), c = mins(s.closes), n = nowMinutes();
    if (o === c) return true;
    return o < c ? n >= o && n < c : n >= o || n < c;
  };
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const norm = (v) => String(v ?? "").toLowerCase().replace(/ё/g, "е").replace(/[ʻʼ'`‘’]/g, "");

  function refreshStatus() {
    STORES.forEach((s) => {
      s.open = isOpen(s);
      const st = items.get(s.id)?.querySelector("[data-status]");
      if (st) {
        st.className = "status " + (s.open ? "status-open" : "status-closed");
        st.textContent = s.opens === s.closes ? T.open24 : s.open ? T.open : T.closed;
      }
      markers.get(s.id)?.setIcon(pinIcon({ selected: s.id === selected, closed: !s.open }));
    });
  }

  function initMap() {
    if (!window.L) return;
    map = baseMap("map");
    const pts = [];
    STORES.forEach((s) => {
      if (s.lat == null || s.lng == null) return;
      const m = L.marker([s.lat, s.lng], { icon: pinIcon({}), title: s.name, keyboard: true });
      m.bindPopup(`<b>${esc(s.name)}</b>${esc(s.address)}<br>${s.opens === s.closes ? esc(T.open24) : esc(s.opens) + "–" + esc(s.closes)}<br><a href="${esc(s.url)}">${esc(T.more)}</a> · <a href="${esc(s.route)}" target="_blank" rel="noopener">${esc(T.route)}</a>`);
      m.on("click", () => select(s.id, false));
      m.addTo(map);
      markers.set(s.id, m);
      pts.push([s.lat, s.lng]);
    });
    if (pts.length > 1) map.fitBounds(pts, { padding: [40, 40] });
  }

  function select(id, fly) {
    const prev = selected;
    selected = id;
    [prev, id].forEach((x) => {
      const s = STORES.find((v) => v.id === x);
      if (s) markers.get(x)?.setIcon(pinIcon({ selected: x === id, closed: !s.open }));
    });
    items.forEach((el, k) => el.classList.toggle("is-selected", k === id));
    const el = items.get(id);
    if (el && !fly) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    const m = markers.get(id);
    if (m && fly && map) { map.flyTo(m.getLatLng(), 15, { duration: 0.5 }); m.openPopup(); }
  }

  function distKm(a, b) {
    const r = (x) => (x * Math.PI) / 180;
    const h = Math.sin(r(b.lat - a.lat) / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(r(b.lng - a.lng) / 2) ** 2;
    return 12742 * Math.asin(Math.sqrt(h));
  }

  function apply() {
    const q = norm(qInput.value.trim());
    const district = districtSel ? districtSel.value : "";
    const city = citySel ? citySel.value : "";
    const order = [...STORES];
    if (userPos) order.sort((a, b) => (a.km ?? 1e9) - (b.km ?? 1e9));
    let shown = 0;
    order.forEach((s) => {
      const el = items.get(s.id);
      if (!el) return;
      const hay = norm([s.name, s.address, s.landmark, s.city, s.district, s.metro].join(" "));
      const ok = (!q || hay.includes(q)) && (!city || s.city === city) && (!district || s.district === district) && (!onlyOpen || s.open);
      el.hidden = !ok;
      if (ok) shown++;
      list.insertBefore(el, emptyEl);
      const d = el.querySelector("[data-dist]");
      if (d) d.textContent = s.km != null ? `${s.km < 10 ? s.km.toFixed(1) : Math.round(s.km)} ${T.km}` : "";
      const m = markers.get(s.id);
      if (m && map) ok ? m.addTo(map) : m.remove();
    });
    emptyEl.hidden = shown > 0;
    countEl.textContent = `${shown} / ${STORES.length}`;
  }

  function locate() {
    if (!navigator.geolocation) { alert(T.geoFail); return; }
    nearBtn.setAttribute("aria-pressed", "true");
    navigator.geolocation.getCurrentPosition((pos) => {
      userPos = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      STORES.forEach((s) => { s.km = s.lat != null ? distKm(userPos, s) : null; });
      apply();
      list.scrollTop = 0;
      if (map) {
        userMarker?.remove();
        userMarker = L.circleMarker([userPos.lat, userPos.lng], { radius: 8, color: "#fff", weight: 3, fillColor: "#1E6FD9", fillOpacity: 1 }).addTo(map);
      }
      const nearest = STORES.filter((s) => s.km != null).sort((a, b) => a.km - b.km)[0];
      if (nearest) select(nearest.id, true);
    }, () => { nearBtn.setAttribute("aria-pressed", "false"); alert(T.geoFail); }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
  }

  items.forEach((el, id) => el.addEventListener("click", (e) => { if (!e.target.closest("a")) select(id, true); }));
  qInput.addEventListener("input", apply);
  districtSel?.addEventListener("change", apply);
  citySel?.addEventListener("change", apply);
  openBtn.addEventListener("click", () => { onlyOpen = !onlyOpen; openBtn.setAttribute("aria-pressed", String(onlyOpen)); apply(); });
  nearBtn.addEventListener("click", locate);
  root.querySelectorAll(".view-tabs button").forEach((b) => b.addEventListener("click", () => {
    layout.dataset.view = b.dataset.view;
    root.querySelectorAll(".view-tabs button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    if (b.dataset.view === "map" && map) setTimeout(() => map.invalidateSize(), 50);
  }));

  initMap();
  refreshStatus();
  apply();
  setInterval(refreshStatus, 60000);
  if (new URLSearchParams(location.search).get("near") === "1") locate();
})();
