/* Shared by both pages: language switch, theme watchers, tooltip, data loading and the base map. */
const BG = (function () {
  const root = document.documentElement;
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
                  set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  const hash = (location.hash || "").replace("#", "");
  let lang = store.get("bg-lang") || ((navigator.language || "en").toLowerCase().startsWith("ru") ? "ru" : "en");
  if (hash === "ru" || hash === "en") lang = hash;
  const titles = { ru: document.title, en: document.title };
  function setLang(l) {
    lang = l; root.dataset.lang = l; root.lang = l; store.set("bg-lang", l);
    document.title = titles[l];
    document.querySelectorAll("[data-aria-ru]").forEach(e => e.setAttribute("aria-label", l === "ru" ? e.dataset.ariaRu : e.dataset.ariaEn));
    document.querySelectorAll("[data-set-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.setLang === l)));
    window.dispatchEvent(new Event("bg-lang"));
  }
  document.querySelectorAll("[data-set-lang]").forEach(b => b.addEventListener("click", () => setLang(b.dataset.setLang)));
  function setTitles(ru, en) { titles.ru = ru; titles.en = en; document.title = titles[lang]; }

  const css = n => getComputedStyle(root).getPropertyValue(n).trim();
  const T = (ru, en) => (lang === "ru" ? ru : en);
  const fmt = (x, d = 0) => Number(x).toLocaleString(lang === "ru" ? "ru-RU" : "en-GB",
    { minimumFractionDigits: d, maximumFractionDigits: d });
  const tip = document.getElementById("tip");
  function showTip(html, x, y) {
    tip.innerHTML = html; tip.hidden = false;
    const r = tip.getBoundingClientRect();
    const px = Math.min(window.scrollX + x + 14, window.scrollX + document.documentElement.clientWidth - r.width - 8);
    tip.style.left = Math.max(window.scrollX + 8, px) + "px"; tip.style.top = (window.scrollY + y + 14) + "px";
  }
  const hideTip = () => { tip.hidden = true; };
  const themeWatchers = [];
  const onTheme = fn => themeWatchers.push(fn);
  const fire = () => themeWatchers.forEach(f => f());
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", fire);
  new MutationObserver(fire).observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  window.addEventListener("bg-lang", fire);
  const getJSON = p => fetch(p).then(r => { if (!r.ok) throw new Error(p + " " + r.status); return r.json(); });

  function loadError(id, ru = "Не удалось загрузить данные. Обновите страницу.", en = "The data could not be loaded. Please reload the page.") {
    document.getElementById(id).innerHTML = `<div class="maperr"><span lang="ru">${ru}</span><span lang="en">${en}</span></div>`;
  }
  const mapError = id => loadError(id, "Не удалось загрузить карту. Обновите страницу.", "The map could not be loaded. Please reload the page.");

  /* The page can start inside a 0×0 frame (claude.ai renders artifacts that way before showing them). A Leaflet map
     created there fits Belgrade into zero pixels and never recovers, so the map is created only once its box has a
     size, and it re-fits the city whenever the box changes until the reader pans or zooms. */
  function whenSized(el, fn) {
    if (el.clientWidth > 0 && el.clientHeight > 0) { fn(); return; }
    const ro = new ResizeObserver(() => { if (el.clientWidth > 0 && el.clientHeight > 0) { ro.disconnect(); fn(); } });
    ro.observe(el);
  }
  function baseMap(id, ctx, ready) {
    if (typeof L === "undefined") { mapError(id); return; }
    const el = document.getElementById(id);
    whenSized(el, () => {
      const map = L.map(el, { preferCanvas: true, zoomSnap: 0.25, attributionControl: true, scrollWheelZoom: false });
      map.attributionControl.setPrefix(false);
      map.attributionControl.addAttribution("© OpenStreetMap contributors · ESA WorldCover");
      const water = L.geoJSON(ctx.water, { interactive: false });
      const roads = L.geoJSON(ctx.roads, { interactive: false });
      const units = L.geoJSON(ctx.units, { interactive: false });
      function style() {
        water.setStyle({ stroke: false, fillColor: css("--water"), fillOpacity: 1 });
        roads.setStyle({ color: css("--road"), weight: 1, opacity: 1 });
        units.setStyle({ color: css("--unit"), weight: 0.8, fill: false, opacity: 1 });
      }
      const bounds = units.getBounds();
      let fitting = false, moved = false;
      const fit = () => { fitting = true; map.fitBounds(bounds, { padding: [10, 10], animate: false }); fitting = false; };
      fit();  /* the view must exist before canvas layers are added */
      water.addTo(map); roads.addTo(map); units.addTo(map); style(); onTheme(style);
      map.on("movestart zoomstart", () => { if (!fitting) moved = true; });
      new ResizeObserver(() => {
        if (!el.clientWidth || !el.clientHeight) return;
        map.invalidateSize({ pan: false });
        if (!moved) fit();
      }).observe(el);
      map.once("focus", () => map.scrollWheelZoom.enable());
      ready(map);
    });
  }

  setLang(lang);
  return { T, fmt, css, showTip, hideTip, onTheme, getJSON, baseMap, mapError, loadError, setTitles, get lang() { return lang; } };
})();
