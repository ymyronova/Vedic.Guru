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
(async () => {
  const dot = document.getElementById("status-dot");
  try {
    const r = await fetch("/api/health");
    const d = await r.json();
    if (dot){ dot.classList.add("ok"); dot.title = "сервер на связи" + (d.ai ? " · тексты Claude включены" : " · шаблонный режим (нет ключа)"); }
    console.info("health:", d);
  } catch (e) {
    if (dot){ dot.classList.add("bad"); dot.title = "нет связи с сервером"; }
    showFatal("не удаётся связаться с сервером: " + e.message);
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
  let i = 0; $("loader-text").textContent = LOAD_MSGS[0];
  loadTimer = setInterval(() => { i = (i+1) % LOAD_MSGS.length; $("loader-text").textContent = LOAD_MSGS[i]; }, 1600);
}
function hideLoader(){ $("loader").classList.add("hidden"); clearInterval(loadTimer); }

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

async function api(path, body){
  const r = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || "Ошибка расчёта");
  return data;
}

// ---- Step 1: rectify ----
$("go").addEventListener("click", async () => {
  $("err").textContent = "";
  const p = birthPayload();
  if (!p.date){ $("err").textContent = "Укажите дату рождения."; return; }
  if (!p.place && !(p.lat && p.lon)){ $("err").textContent = "Укажите место рождения или координаты."; return; }
  showLoader();
  try{
    const res = await api("/api/rectify", p);
    $("lagna-badge").textContent = res.ascendant.sign_ru + " " + res.ascendant.dms;
    $("lagna-desc").textContent = res.description.main;
    $("lagna-confirm").textContent = res.description.confirm;
    $("form-panel").classList.add("hidden");
    $("rectify-panel").classList.remove("hidden");
    window.scrollTo({top:0, behavior:"smooth"});
  }catch(e){ $("err").textContent = e.message; }
  finally{ hideLoader(); }
});

// ---- Step 2: full almanac ----
$("confirm-yes").addEventListener("click", async () => {
  const p = birthPayload();
  lastName = p.name;
  showLoader();
  try{
    const res = await api("/api/almanac", p);
    lastAlmanacHtml = res.html;
    $("frame").srcdoc = res.html;
    $("rectify-panel").classList.add("hidden");
    $("result-panel").classList.remove("hidden");
    if (!res.has_ai){
      // gentle notice if API key not set
      console.info("ANTHROPIC_API_KEY не задан — тексты в шаблонном режиме.");
    }
    window.scrollTo({top:0, behavior:"smooth"});
  }catch(e){ alert(e.message); }
  finally{ hideLoader(); }
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
  $("rectify-panel").classList.add("hidden");
  $("events-panel").classList.remove("hidden");
  window.scrollTo({top:0, behavior:"smooth"});
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
    renderRanked(r);
    $("events-panel").classList.add("hidden");
    $("rectify-results-panel").classList.remove("hidden");
    window.scrollTo({top:0, behavior:"smooth"});
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
  $("time").value = time;
  const un = $("unknown-time"); if (un) un.checked = false;
  const p = birthPayload();
  lastName = p.name;
  showLoader();
  try{
    const res = await api("/api/almanac", p);
    lastAlmanacHtml = res.html;
    $("frame").srcdoc = res.html;
    $("rectify-results-panel").classList.add("hidden");
    $("result-panel").classList.remove("hidden");
    window.scrollTo({top:0, behavior:"smooth"});
  }catch(e){ alert(e.message); }
  finally{ hideLoader(); }
}

$("restart").addEventListener("click", () => {
  ["result-panel","rectify-panel","events-panel","rectify-results-panel"].forEach(id => $(id).classList.add("hidden"));
  const compat = document.querySelector(".mode-btn.active")?.dataset.mode === "compat";
  $("syn-panel").classList.toggle("hidden", !compat);
  $("form-panel").classList.toggle("hidden", compat);
  window.scrollTo({top:0, behavior:"smooth"});
});

$("download").addEventListener("click", () => {
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
    const compat = btn.dataset.mode === "compat";
    ["rectify-panel","events-panel","rectify-results-panel","result-panel"].forEach(id => $(id).classList.add("hidden"));
    $("form-panel").classList.toggle("hidden", compat);
    $("syn-panel").classList.toggle("hidden", !compat);
    window.scrollTo({top:0, behavior:"smooth"});
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
  if ((!a.place && !(a.lat&&a.lon)) || (!b.place && !(b.lat&&b.lon))){
    $("syn-err").textContent = "Укажите место (или координаты) для обоих."; return; }
  lastName = (a.name + "_x_" + b.name);
  showLoader();
  try{
    const res = await api("/api/synastry", {person_a:a, person_b:b});
    lastAlmanacHtml = res.html;
    $("frame").srcdoc = res.html;
    $("syn-panel").classList.add("hidden");
    $("result-panel").classList.remove("hidden");
    window.scrollTo({top:0, behavior:"smooth"});
  }catch(e){ $("syn-err").textContent = e.message; }
  finally{ hideLoader(); }
});
