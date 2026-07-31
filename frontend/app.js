const $ = id => document.getElementById(id);
let lastAlmanacHtml = null, lastName = "almanac";

// ---- surface any error visibly (so remote debugging is possible) ----
function showFatal(msg){
  const b = document.getElementById("fatal-banner");
  if (b){ b.textContent = "⚠ Ошибка в браузере: " + msg + "\n(скопируйте это сообщение)"; b.classList.add("show"); }
}
window.addEventListener("error", e => showFatal((e.message||"") + (e.filename?` @ ${e.filename}:${e.lineno}`:"")));
window.addEventListener("unhandledrejection", e => showFatal("promise: " + (e.reason && (e.reason.message||e.reason) || "unknown")));

// ---- connection self-test on load: proves JS runs and server is reachable ----
// Retries while the instance wakes: on the free tier it sleeps after ~15 minutes
// idle, and the first request lands on a proxy page. Failing outright there put
// up a red dot and a scary banner for a server that was simply starting.
(async () => {
  const dot = document.getElementById("status-dot");
  const setDot = (cls, title) => {
    if (!dot) return;
    dot.classList.remove("ok", "bad", "warn");
    if (cls) dot.classList.add(cls);
    dot.title = title;
  };
  setDot(null, "проверка связи…");

  for (let attempt = 1; attempt <= 4; attempt++){
    try{
      const r = await fetch("/api/health", {cache: "no-store"});
      const raw = await r.text();
      const d = JSON.parse(raw);          // throws on a gateway page, not on our JSON
      setDot(d.ai ? "ok" : "warn",
             d.ai ? "сервер на связи · тексты Claude включены"
                  // ai_detail names the real cause (bad key / no credit / wrong
                  // model); the old tooltip always claimed "нет ключа".
                  : "сервер на связи · шаблонный режим — " + (d.ai_detail || "Claude недоступен"));
      console.info("health:", d);
      return;
    }catch(e){
      if (attempt === 4){
        setDot("bad", "нет связи с сервером");
        showFatal("не удаётся связаться с сервером: " + e.message);
        return;
      }
      setDot("warn", "сервер просыпается…");
      await new Promise(res => setTimeout(res, attempt * 2000));
    }
  }
})();

const LOAD_MSGS = [
  "Считаю положения планет…",
  "Развожу дома по знакам…",
  "Взвешиваю варги (Вимшопака)…",
  "Складываю бинду по домам…",
  "Разворачиваю дугу даш…",
  "Собираю альманах…",
];
let loadTimer = null;
function showLoader(){
  const l = $("loader"); l.classList.remove("hidden");
  let i = 0, ticks = 0;
  // A full almanac takes ~70s, and longer on a cold start. Say so once it has
  // been a while, so a normal wait doesn't read as a hang.
  const paint = () => {
    const slow = ticks * 1.6 >= 25 ? "  ·  обычно до минуты" : "";
    $("loader-text").textContent = LOAD_MSGS[i] + slow;
  };
  paint();
  loadTimer = setInterval(() => { ticks++; i = (i+1) % LOAD_MSGS.length; paint(); }, 1600);
}
function hideLoader(){ $("loader").classList.add("hidden"); clearInterval(loadTimer); }

// ---- live geocoding ----------------------------------------------------
// As the user types a city we resolve it and fill the coordinate fields, so
// what the form shows is always what the calculation will actually use.
// Fields the user edited by hand are never overwritten.
function attachGeocoder(placeId, latId, lonId, tzId, statusId){
  const placeEl = $(placeId), latEl = $(latId), lonEl = $(lonId),
        tzEl = $(tzId), st = $(statusId);
  if (!placeEl || !st) return;
  let timer = null, seq = 0;

  // Typing in a coordinate field hands ownership of it to the user.
  [latEl, lonEl, tzEl].forEach(el => el && el.addEventListener("input", () => {
    delete el.dataset.auto;
  }));

  const setAuto = (el, val) => {
    if (!el) return;
    if (el.value && el.dataset.auto !== "1") return;  // user typed it — leave alone
    el.value = val; el.dataset.auto = "1";
  };
  const clearAuto = el => {
    if (el && el.dataset.auto === "1"){ el.value = ""; delete el.dataset.auto; }
  };

  async function lookup(){
    const q = placeEl.value.trim();
    if (!q){ st.textContent = ""; st.className = "geo"; [latEl,lonEl,tzEl].forEach(clearAuto); return; }
    const mine = ++seq;                                  // drop out-of-order replies
    st.textContent = "Ищу координаты…"; st.className = "geo";
    try{
      const r = await fetch("/api/geocode?place=" + encodeURIComponent(q));
      const d = await r.json();
      if (mine !== seq) return;
      if (!r.ok) throw new Error(d.detail || "город не найден");
      setAuto(latEl, d.lat.toFixed(4));
      setAuto(lonEl, d.lon.toFixed(4));
      setAuto(tzEl, d.tz);
      const where = d.label + (d.cc ? ` (${d.cc})` : "");
      st.textContent = `✓ ${where} · ${d.lat.toFixed(4)}, ${d.lon.toFixed(4)} · ${d.tz}`;
      st.className = "geo ok";
    }catch(e){
      if (mine !== seq) return;
      [latEl,lonEl,tzEl].forEach(clearAuto);
      st.textContent = "✕ " + e.message + " — введите координаты вручную.";
      st.className = "geo bad";
    }
  }

  placeEl.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(lookup, 450); });
  placeEl.addEventListener("blur", () => { clearTimeout(timer); lookup(); });
}

attachGeocoder("place",   "lat",   "lon",   "tz",   "geo-status");
attachGeocoder("a-place", "a-lat", "a-lon", "a-tz", "a-geo-status");
attachGeocoder("b-place", "b-lat", "b-lon", "b-tz", "b-geo-status");

// ---- step navigation ------------------------------------------------------
// Panels were previously toggled ad-hoc with .hidden in eight places, so there
// was no way back and the almanac iframe was overwritten by each new run. This
// keeps a stack of visited steps together with the payload each one needs, so
// returning to a step re-renders exactly what it showed before — including an
// earlier almanac. Wired to the History API so the browser's own back button
// and swipe-back gesture move between steps instead of leaving the app.
const PANELS = ["form-panel", "syn-panel", "rectify-panel", "events-panel",
                "rectify-results-panel", "result-panel"];

const PANEL_LABELS = {
  "form-panel":            "Данные",
  "syn-panel":             "Двое",
  "rectify-panel":         "Лагна",
  "events-panel":          "События",
  "rectify-results-panel": "Варианты",
  "result-panel":          "Альманах",
};

// How to rebuild a step's contents from its stored payload. Panels made only of
// form inputs need no entry — the DOM keeps what was typed, since panels are
// hidden rather than cleared.
const RESTORE = {
  "rectify-panel": d => {
    $("lagna-badge").textContent = d.ascendant.sign_ru + " " + d.ascendant.dms;
    $("lagna-desc").textContent = d.description.main;
    $("lagna-confirm").textContent = d.description.confirm;
  },
  "rectify-results-panel": d => renderRanked(d),
  "result-panel": d => {
    // Also restore the download target, so saving gives the almanac on screen
    // rather than whichever one was generated last.
    lastAlmanacHtml = d.html;
    lastName = d.name || lastName;
    if ($("frame").srcdoc !== d.html) $("frame").srcdoc = d.html;
    // Fresh arrival: hide the print hint again. The click handler decides
    // whether this user has earned it.
    $("print-hint").classList.add("hidden");
  },
};

const NAV = { stack: [], i: -1, restoring: false };

function showOnly(panel){
  PANELS.forEach(id => { const el = $(id); if (el) el.classList.toggle("hidden", id !== panel); });
}

function renderNavBar(){
  const bar = $("nav-bar");
  if (!bar) return;
  // Nothing to navigate until there is more than one step.
  bar.classList.toggle("hidden", NAV.stack.length < 2);
  $("nav-back").disabled = NAV.i <= 0;
  $("nav-fwd").disabled  = NAV.i >= NAV.stack.length - 1;

  const crumbs = $("nav-crumbs");
  crumbs.innerHTML = "";
  NAV.stack.forEach((step, idx) => {
    const li = document.createElement("li");
    li.className = "nav-crumb" + (idx === NAV.i ? " current" : "")
                 + (idx > NAV.i ? " ahead" : "");
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = PANEL_LABELS[step.panel] || step.panel;
    b.addEventListener("click", () => navTo(idx));
    li.appendChild(b);
    crumbs.appendChild(li);
  });
}

function applyStep(){
  const step = NAV.stack[NAV.i];
  if (!step) return;
  showOnly(step.panel);
  // The result step reads as a document and needs the width; the form steps do
  // not. Driven from here so it stays correct on back/forward too.
  document.body.classList.toggle("wide", step.panel === "result-panel");
  const restore = RESTORE[step.panel];
  if (restore && step.data){
    NAV.restoring = true;
    try { restore(step.data); } finally { NAV.restoring = false; }
  }
  renderNavBar();
  window.scrollTo({top:0, behavior:"smooth"});
}

function navGo(panel, data){
  // Taking a new action from a step discards anything that was ahead of it.
  NAV.stack = NAV.stack.slice(0, NAV.i + 1);
  NAV.stack.push({panel, data: data ?? null});
  NAV.i = NAV.stack.length - 1;
  applyStep();
  history.pushState({navIndex: NAV.i}, "", "#" + panel);
}

function navTo(i){
  if (i < 0 || i >= NAV.stack.length || i === NAV.i) return;
  NAV.i = i;
  applyStep();
  history.pushState({navIndex: NAV.i}, "", "#" + NAV.stack[i].panel);
}

function navReset(panel){
  NAV.stack = [{panel, data: null}];
  NAV.i = 0;
  applyStep();
  history.replaceState({navIndex: 0}, "", "#" + panel);
}

$("nav-back").addEventListener("click", () => navTo(NAV.i - 1));
$("nav-fwd").addEventListener("click",  () => navTo(NAV.i + 1));

window.addEventListener("popstate", e => {
  const i = e.state && typeof e.state.navIndex === "number" ? e.state.navIndex : 0;
  if (i >= 0 && i < NAV.stack.length){
    NAV.i = i;
    applyStep();          // no pushState here — the browser already moved
  }
});

document.addEventListener("keydown", e => {
  // Alt+←/→ mirrors the browser shortcut, but only outside a text field.
  if (!e.altKey || /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement?.tagName || "")) return;
  if (e.key === "ArrowLeft"){ e.preventDefault(); navTo(NAV.i - 1); }
  if (e.key === "ArrowRight"){ e.preventDefault(); navTo(NAV.i + 1); }
});

// Seed the stack with the opening panel, so the first step is itself a history
// entry and the first navGo() doesn't drop it.
navReset("form-panel");

function birthPayload(){
  const p = {
    name: $("name").value.trim() || "Гость",
    date: $("date").value,
    time: $("time").value || "12:00",
    place: $("place").value.trim() || null,
  };
  const lat = $("lat").value, lon = $("lon").value, tz = $("tz").value.trim();
  if (lat && lon){ p.lat = parseFloat(lat); p.lon = parseFloat(lon); }
  if (tz) p.tz = tz;
  return p;
}

// A non-JSON response is almost always a gateway page rather than anything this
// app produced: on the free tier the instance sleeps after ~15 minutes idle and
// the proxy answers with HTML while it wakes. r.json() turned that into
// "Unexpected token '<'", which tells the user nothing and looks like a bug in
// the app. Name the actual situation instead.
function gatewayMessage(status, raw){
  const html = /^\s*<(!doctype|html)/i.test(raw || "");
  if (status === 502 || status === 503 || status === 504 || status === 0)
    return `Сервер не ответил (${status || "нет ответа"}). На бесплатном тарифе он ` +
           `засыпает при простое и просыпается ~минуту — попробуйте ещё раз.`;
  if (html)
    return `Сервер вернул страницу вместо данных (HTTP ${status}) — запрос не дошёл ` +
           `до приложения. Подождите минуту и повторите.`;
  return `Неожиданный ответ сервера (HTTP ${status}).`;
}

async function api(path, body){
  let r;
  try{
    r = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  }catch(e){
    throw new Error("Нет связи с сервером: " + e.message);
  }
  const raw = await r.text();
  let data;
  try{
    data = raw ? JSON.parse(raw) : {};
  }catch{
    throw new Error(gatewayMessage(r.status, raw));
  }
  if (!r.ok){
    // The verification gate (409) returns a structured detail object, not a
    // string — render its message rather than "[object Object]".
    const d = data.detail;
    const msg = (d && typeof d === "object")
      ? (d.message || JSON.stringify(d))
      : (d || "Ошибка расчёта");
    const err = new Error(msg);
    err.detail = d;
    throw err;
  }
  return data;
}

// ---- lagna step: first-timers only ----------------------------------------
// Confirming the lagna is orientation, not a calculation input: it exists so a
// newcomer can sanity-check the birth time before a long generation. Someone
// who has already been through it once knows their lagna, so the step is pure
// friction — and it costs a Claude call. Returning visitors go straight to the
// almanac, with "Сначала уточнить лагну" left as the way back in, since that
// panel is also the only entrance to event-based rectification.
const SEEN_LAGNA_KEY = "jyotish.seenLagnaStep";
const seenLagnaStep = () => {
  // Storage throws in private mode; treat that as a first visit. Showing the
  // step again is harmless, an exception in the main button is not.
  try { return localStorage.getItem(SEEN_LAGNA_KEY) === "1"; }
  catch { return false; }
};
const markLagnaSeen = () => {
  try { localStorage.setItem(SEEN_LAGNA_KEY, "1"); } catch {}
};

// ---- remembered birth details ---------------------------------------------
// There is no account system, so "credentials" here are the birth details kept
// in this browser. Saved once rectification has settled a time, so the value
// stored is the reconstructed one rather than the 12:00 placeholder the user
// started from — and restored on the next visit so nothing is retyped.
const PROFILE_KEY = "jyotish.birth";

function saveProfile(p){
  try{
    localStorage.setItem(PROFILE_KEY, JSON.stringify({
      name: p.name || "", date: p.date || "", time: p.time || "",
      place: $("place").value.trim() || "",
      lat: $("lat").value || "", lon: $("lon").value || "", tz: $("tz").value.trim() || "",
      saved_at: new Date().toISOString(),
    }));
  }catch{}                      // private mode: remembering is a nicety, not a feature
}

function loadProfile(){
  try{ return JSON.parse(localStorage.getItem(PROFILE_KEY) || "null"); }
  catch{ return null; }
}

function restoreProfile(){
  const p = loadProfile();
  if (!p) return false;
  const set = (id, v) => { if (v && $(id) && !$(id).value) $(id).value = v; };
  set("name", p.name); set("date", p.date); set("time", p.time);
  set("place", p.place); set("lat", p.lat); set("lon", p.lon); set("tz", p.tz);
  if (p.place && $("geo-status") && p.lat && p.lon){
    $("geo-status").textContent = `✓ сохранено: ${p.place} · ${p.lat}, ${p.lon}`
                                + (p.tz ? ` · ${p.tz}` : "");
    $("geo-status").className = "geo ok";
  }
  return true;
}

const timeUnknown = () => $("no-time").checked;

function applyReturningVisitor(){
  const returning = seenLagnaStep();
  // Ticking "не знаю" outranks everything: with no time there is nothing to
  // confirm, so the button leads to reconstruction rather than to a chart.
  $("go").textContent = timeUnknown() ? "Подобрать время по событиям →"
                      : returning     ? "Собрать альманах →"
                                      : "Рассчитать лагну →";
  $("go-lagna").classList.toggle("hidden", !returning || timeUnknown());
}

// Ticking the box empties and disables the time field, so a stale 12:00 cannot
// be mistaken for a real value — by the user or by the payload.
$("no-time").addEventListener("change", () => {
  const off = timeUnknown();
  $("time").disabled = off;
  $("time").value = off ? "" : "12:00";
  const un = $("unknown-time");           // mirror it on the events panel
  if (un) un.checked = off;
  applyReturningVisitor();
});

applyReturningVisitor();

if (restoreProfile()) $("forget-profile").classList.remove("hidden");

// Birth details are personal, so leaving them in the browser with no way out
// would be wrong. One click clears both the details and the returning-visitor
// flag, putting the app back to how a newcomer finds it.
$("forget-profile").addEventListener("click", () => {
  try{
    localStorage.removeItem(PROFILE_KEY);
    localStorage.removeItem(SEEN_LAGNA_KEY);
  }catch{}
  ["name","date","time","place","lat","lon","tz"].forEach(id => { if ($(id)) $(id).value = ""; });
  $("time").value = "12:00";
  if ($("geo-status")){ $("geo-status").textContent = ""; $("geo-status").className = "geo"; }
  $("forget-profile").classList.add("hidden");
  applyReturningVisitor();
});

function validBirth(p){
  if (!p.date){ $("err").textContent = "Укажите дату рождения."; return false; }
  // With "не знаю" ticked the time field is empty by design, so it is not
  // required — the events flow reconstructs it.
  if (!timeUnknown() && !p.time){ $("err").textContent = "Укажите время или отметьте «не знаю»."; return false; }
  if (!p.place && !(Number.isFinite(p.lat) && Number.isFinite(p.lon))){
    $("err").textContent = "Укажите место рождения или координаты."; return false; }
  return true;
}

async function buildAlmanac(p){
  lastName = p.name;
  showLoader();
  try{
    const res = await api("/api/almanac", p);
    navGo("result-panel", {html: res.html, name: p.name});
    markLagnaSeen();          // they have now seen a finished chart
    // Remember the details that produced this chart. Reached from rectification
    // too, where p.time is the reconstructed time rather than the placeholder.
    saveProfile(p);
    applyReturningVisitor();
    if (!res.has_ai){
      console.info("Claude недоступен — тексты в шаблонном режиме. Подробности: /api/ai");
    }
  }catch(e){ alert(e.message); }
  finally{ hideLoader(); }
}

async function goToLagna(p){
  showLoader();
  try{
    const res = await api("/api/rectify", p);
    navGo("rectify-panel", res);
  }catch(e){ $("err").textContent = e.message; }
  finally{ hideLoader(); }
}

// ---- Step 1 ----
$("go").addEventListener("click", async () => {
  $("err").textContent = "";
  const p = birthPayload();
  if (!validBirth(p)) return;
  if (timeUnknown())        await goToRectification();
  else if (seenLagnaStep()) await buildAlmanac(p);   // skip the confirmation
  else                      await goToLagna(p);
});

// Explicit way back to the lagna step, and thus to event rectification.
$("go-lagna").addEventListener("click", async () => {
  $("err").textContent = "";
  const p = birthPayload();
  if (!validBirth(p)) return;
  await goToLagna(p);
});

// Without a time the lagna is undetermined, so confirming one would be theatre.
// Go straight to reconstruction from life events, scanning the whole day.
async function goToRectification(){
  await loadCatalog();
  const list = $("events-list");
  if (!list.children.length){
    list.appendChild(eventRow()); list.appendChild(eventRow()); list.appendChild(eventRow());
  }
  const un = $("unknown-time");
  if (un) un.checked = true;
  navGo("events-panel", null);
}

// ---- Step 2: full almanac ----
$("confirm-yes").addEventListener("click", async () => {
  await buildAlmanac(birthPayload());
});

// ---- Step 1.2: event-based rectification ----
let EVENT_CATALOG = [];
async function loadCatalog(){
  if (EVENT_CATALOG.length) return;
  try{ EVENT_CATALOG = (await (await fetch("/api/events")).json()).events; }catch(e){}
}
function eventRow(){
  const row = document.createElement("div");
  row.className = "ev-row";
  const opts = EVENT_CATALOG.map(e => `<option value="${e.key}">${e.label}</option>`).join("");
  row.innerHTML =
    `<input class="ev-date" type="text" placeholder="Год / ГГГГ-ММ" maxlength="10">
     <select class="ev-cat"><option value="">— тип события —</option>${opts}</select>
     <button class="ev-del" title="Удалить">×</button>`;
  row.querySelector(".ev-del").addEventListener("click", () => row.remove());
  return row;
}

$("confirm-no").addEventListener("click", async () => {
  await loadCatalog();
  const list = $("events-list");
  if (!list.children.length){ list.appendChild(eventRow()); list.appendChild(eventRow()); list.appendChild(eventRow()); }
  navGo("events-panel", null);
});

$("add-event").addEventListener("click", () => $("events-list").appendChild(eventRow()));

$("unknown-time").addEventListener("change", e => {
  $("time").value = e.target.checked ? "" : ($("time").value || "12:00");
});

$("find-lagna").addEventListener("click", async () => {
  $("events-err").textContent = "";
  const events = [...document.querySelectorAll(".ev-row")].map(r => ({
    date: r.querySelector(".ev-date").value.trim(),
    category: r.querySelector(".ev-cat").value || null,
    note: ""
  })).filter(e => e.date && e.category);
  if (events.length < 1){ $("events-err").textContent = "Добавьте хотя бы одно событие (год + тип)."; return; }

  const p = birthPayload();
  p.events = events;
  p.known_time = !$("unknown-time").checked;
  if (!p.known_time) p.time = "12:00";  // placeholder; engine scans the whole day

  showLoader();
  try{
    const r = await api("/api/rectify_events", p);
    navGo("rectify-results-panel", r);   // RESTORE calls renderRanked
  }catch(e){ $("events-err").textContent = e.message; }
  finally{ hideLoader(); }
});

function renderRanked(r){
  const cb = $("conf-badge");
  cb.textContent = "уверенность: " + r.confidence;
  cb.className = "conf " + (r.confidence === "высокая" ? "high" : r.confidence === "средняя" ? "mid" : "low");
  $("results-summary").textContent =
    `Проверено ${r.n_candidates} вариантов времени по ${r.n_events} событиям. ` +
    `Наиболее вероятная лагна — ${r.ranked_signs[0].lagna_ru}. Выберите вариант, чтобы собрать альманах.`;

  const list = $("ranked-list"); list.innerHTML = "";
  const max = Math.max(...r.ranked_signs.map(s => s.score)) || 1;
  r.ranked_signs.forEach(s => {
    const el = document.createElement("div");
    el.className = "rank";
    el.innerHTML =
      `<div class="lg">${s.lagna_ru}</div>
       <div class="bar"><i style="width:${Math.round(100*s.score/max)}%"></i></div>
       <div class="meta">${s.share}% · время ${s.best_time}<br>окно ${s.time_from}–${s.time_to}</div>
       <button class="ghost use-time" data-time="${s.best_time}">Собрать →</button>`;
    el.querySelector(".use-time").addEventListener("click", () => generateWithTime(s.best_time));
    list.appendChild(el);
  });

  const ev = $("evidence-list"); ev.innerHTML = "";
  r.best.evidence.forEach(e => {
    const d = document.createElement("div");
    d.className = "ev-why";
    d.innerHTML = `<b>${e.label}</b> <span>(${e.date} · даша ${e.dasha})</span><br>` +
                  `<span>${e.why.join(" · ") || "нет явных совпадений"}</span>`;
    ev.appendChild(d);
  });
}

async function generateWithTime(time){
  // A time is now known, so the field comes back to life and both "не знаю"
  // boxes clear — otherwise the reconstructed time would sit in a greyed-out
  // input and the next run would still scan the whole day.
  $("no-time").checked = false;
  $("time").disabled = false;
  $("time").value = time;
  const un = $("unknown-time"); if (un) un.checked = false;
  applyReturningVisitor();
  await buildAlmanac(birthPayload());
}

$("restart").addEventListener("click", () => {
  // "Start over" deliberately clears history — the old steps described a run
  // the user is abandoning. Form inputs are kept so nothing is retyped.
  const compat = document.querySelector(".mode-btn.active")?.dataset.mode === "compat";
  navReset(compat ? "syn-panel" : "form-panel");
});

// PDF through the browser's own print engine. The almanac already carries
// @page A4, print-color-adjust and full page-break rules, ported from the
// reference document — which was itself produced by printing to PDF. So this
// gives exact pagination, selectable text, embedded fonts and a small file.
//
// Deliberately not a server-side renderer: headless Chromium needs ~300–500 MB
// and would not fit the free tier's 512 MB alongside the city index, and
// WeasyPrint — the light alternative — supports flexbox only partially and CSS
// grid poorly, which this layout uses in the section headers, planet blocks and
// two-column cards. A weaker second renderer would produce a worse PDF than the
// one Chrome already makes from these rules.
function saveBlob(blob, filename){
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// Fallback only: used when the server cannot build the PDF. The almanac carries
// @page A4 and the page-break rules, so the browser's own print dialog produces
// the same document — it just costs the user an extra click.
function printFallback(reason){
  const hint = $("print-hint");
  if (hint){
    hint.innerHTML = "Не удалось собрать PDF на сервере, поэтому открыто окно печати — " +
                     "выберите принтер <b>«Сохранить как PDF»</b>." +
                     (reason ? ` <span style="opacity:.7">(${reason})</span>` : "");
    hint.classList.remove("hidden");
  }
  const f = $("frame");
  try{
    f.contentWindow.focus();
    f.contentWindow.print();
  }catch(e){
    const w = window.open("", "_blank");
    if (w){ w.document.write(lastAlmanacHtml); w.document.close(); w.focus(); }
  }
}

$("download").addEventListener("click", async () => {
  if (!lastAlmanacHtml){ alert("Альманах ещё не готов."); return; }
  const btn = $("download");
  const label = btn.textContent;
  btn.disabled = true; btn.textContent = "Собираю PDF…";
  try{
    const r = await fetch("/api/pdf", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({html: lastAlmanacHtml, filename: lastName || "almanac"}),
    });
    if (!r.ok){
      let why = `HTTP ${r.status}`;
      try{ const d = await r.json(); why = d.detail || why; }catch{}
      throw new Error(why);
    }
    const blob = await r.blob();
    if (blob.type && blob.type.indexOf("pdf") === -1) throw new Error("сервер вернул не PDF");
    saveBlob(blob, (lastName || "almanac").replace(/\s+/g, "_") + ".pdf");
    if ($("print-hint")) $("print-hint").classList.add("hidden");
  }catch(e){
    printFallback(e.message);
  }finally{
    btn.disabled = false; btn.textContent = label;
  }
});

// The HTML stays available as the archivable original — it is self-contained
// (inline CSS, inline SVG, no external fonts), so it opens anywhere, offline.
$("download-html").addEventListener("click", () => {
  if (!lastAlmanacHtml) return;
  const blob = new Blob([lastAlmanacHtml], {type:"text/html"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = (lastName.replace(/\s+/g,"_") || "almanac") + "_almanac.html";
  a.click(); URL.revokeObjectURL(a.href);
});

// ---- mode toggle: personal almanac vs compatibility ----
document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    // Switching mode starts a different flow, so history restarts here too.
    navReset(btn.dataset.mode === "compat" ? "syn-panel" : "form-panel");
  });
});

function personPayload(prefix){
  const g = s => $(prefix + s);
  const p = { name: g("-name").value.trim() || "Партнёр",
              date: g("-date").value, time: g("-time").value || "12:00",
              place: g("-place").value.trim() || null };
  const lat = g("-lat").value, lon = g("-lon").value, tz = g("-tz").value.trim();
  if (lat && lon){ p.lat = parseFloat(lat); p.lon = parseFloat(lon); }
  if (tz) p.tz = tz;
  return p;
}

$("go-syn").addEventListener("click", async () => {
  $("syn-err").textContent = "";
  const a = personPayload("a"), b = personPayload("b");
  if (!a.date || !b.date){ $("syn-err").textContent = "Укажите даты рождения обоих."; return; }
  const hasCoords = q => Number.isFinite(q.lat) && Number.isFinite(q.lon);
  if ((!a.place && !hasCoords(a)) || (!b.place && !hasCoords(b))){
    $("syn-err").textContent = "Укажите место (или координаты) для обоих."; return; }
  lastName = (a.name + "_x_" + b.name);
  showLoader();
  try{
    const res = await api("/api/synastry", {person_a:a, person_b:b});
    navGo("result-panel", {html: res.html, name: lastName});
  }catch(e){ $("syn-err").textContent = e.message; }
  finally{ hideLoader(); }
});
