"use strict";
const API = window.QUEST_API;
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let token = null;
let state = null;
let timer = null;

function saved() {
  try { return localStorage.getItem("dq-token"); } catch (e) { return null; }
}
function save(value) {
  try { value ? localStorage.setItem("dq-token", value) : localStorage.removeItem("dq-token"); } catch (e) { /* private mode */ }
}

async function call(method, path, body) {
  const res = await fetch(API + path, {
    method,
    headers: { "content-type": "application/json", ...(token ? { "x-token": token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || `HTTP ${res.status}`), { status: res.status });
  return data;
}

function toast(text) {
  const el = Object.assign(document.createElement("div"), { className: "toast", textContent: text });
  document.body.append(el);
  setTimeout(() => el.remove(), 3500);
}

function floatPoints(anchor, text) {
  const r = anchor.getBoundingClientRect();
  const el = Object.assign(document.createElement("div"), { className: "float", textContent: text });
  el.style.left = `${r.left + r.width / 2}px`;
  el.style.top = `${r.top}px`;
  document.body.append(el);
  setTimeout(() => el.remove(), 1300);
}

function confetti() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  for (let i = 0; i < 60; i++) {
    const el = Object.assign(document.createElement("div"), { className: "float", textContent: ["🎉", "✨", "🟢", "🔎"][i % 4] });
    el.style.left = `${Math.random() * 100}vw`;
    el.style.top = `${40 + Math.random() * 40}vh`;
    el.style.animationDelay = `${Math.random() * 0.6}s`;
    document.body.append(el);
    setTimeout(() => el.remove(), 2200);
  }
}

// ---- rendering -----------------------------------------------------------------

function render() {
  $("who").textContent = state.nick;
  $("score").textContent = state.score;
  $("progress").textContent = `${state.solvedCount}/${state.totalParts} parts cleared · class ${state.session}${state.status === "closed" ? " (closed)" : ""}`;
  $("barFill").style.width = `${(100 * state.solvedCount) / state.totalParts}%`;
  $("missions").innerHTML = state.questions.map(missionHtml).join("");
  const debrief = $("debrief");
  debrief.classList.toggle("hidden", !state.unlocked);
  if (state.unlocked && !debrief.dataset.ready) {
    debrief.dataset.ready = "1";
    debrief.innerHTML = `<h2>${state.status === "closed" ? "Session closed" : "All missions cleared"}</h2>
      <p class="sub">The explanations are unlocked.</p><button id="showDebrief">Read the debrief</button>`;
    $("showDebrief").onclick = loadDebrief;
  }
}

function missionHtml(q, i) {
  const done = q.parts.every((p) => p.solved != null);
  const parts = q.parts.map((p) => partHtml(q, p)).join("");
  return `<article class="card ${done ? "done" : ""}"><h2>${done ? "✓ " : ""}Mission ${i + 1}: ${esc(q.title)}</h2>
    <p class="prompt">${esc(q.prompt)}</p>${parts}</article>`;
}

function partHtml(q, p) {
  const id = `${q.id}-${p.id}`;
  const head = `<div class="part-head"><span>${esc(p.label)}</span><span class="pts">${p.solved != null ? `+${p.solved}` : `${p.points} pts`}</span></div>`;
  if (p.solved != null) return `<div class="part">${head}<span class="ok">✓ solved</span></div>`;
  const hints = p.hints.map((h) => `<div class="hint">💡 ${esc(h)}</div>`).join("");
  const hintBtn = p.nextHintCost != null ? `<button class="ghost" data-hint="${q.id}|${p.id}">Hint (−${p.nextHintCost} pts)</button>` : "";
  const input = p.type === "mcq"
    ? `<div class="opts">${p.options.map((o, k) => `<button class="opt" data-mcq="${q.id}|${p.id}|${k}">${esc(o)}</button>`).join("")}</div>`
    : `<form class="row" data-text="${q.id}|${p.id}"><input type="text" aria-label="${esc(p.label)}" autocomplete="off" spellcheck="false"><button>Check</button></form>`;
  return `<div class="part" id="${id}">${head}${input}${hints}<div>${hintBtn}</div><p class="err" role="alert"></p></div>`;
}

// ---- actions -------------------------------------------------------------------

async function refresh() {
  state = await call("GET", "/state");
  // re-rendering must not wipe what a student is typing
  const typed = {};
  document.querySelectorAll("form[data-text] input").forEach((i) => { typed[i.closest("form").dataset.text] = i.value; });
  render();
  document.querySelectorAll("form[data-text] input").forEach((i) => { i.value = typed[i.closest("form").dataset.text] || ""; });
}

async function submit(qid, part, value, partEl, anchor) {
  const err = partEl.querySelector(".err");
  err.textContent = "";
  try {
    const res = await call("POST", "/answer", { qid, part, value });
    if (!res.correct) {
      partEl.classList.remove("shake");
      void partEl.offsetWidth;
      partEl.classList.add("shake");
      err.textContent = `Not quite. ${res.attemptsLeft} attempt(s) left before a 1 min pause.`;
      return;
    }
    floatPoints(anchor, `+${res.points}`);
    if (res.firstBlood) toast(`🩸 First blood #${res.firstBlood.rank}: +${res.firstBlood.bonus} bonus pts`);
    const wasUnlocked = state.unlocked;
    await refresh();
    if (!wasUnlocked && state.unlocked) confetti();
  } catch (e) {
    err.textContent = e.message;
  }
}

document.addEventListener("click", async (ev) => {
  const t = ev.target.closest("button");
  if (!t) return;
  if (t.dataset.mcq) {
    const [qid, part, k] = t.dataset.mcq.split("|");
    submit(qid, part, Number(k), t.closest(".part"), t);
  } else if (t.dataset.hint) {
    const [qid, part] = t.dataset.hint.split("|");
    const err = t.closest(".part").querySelector(".err");
    try { await call("POST", "/hint", { qid, part }); await refresh(); } catch (e) { err.textContent = e.message; }
  }
});

document.addEventListener("submit", (ev) => {
  const f = ev.target.closest("form[data-text]");
  if (!f) return;
  ev.preventDefault();
  const [qid, part] = f.dataset.text.split("|");
  submit(qid, part, f.querySelector("input").value, f.closest(".part"), f.querySelector("button"));
});

async function loadDebrief() {
  const { explanations } = await call("GET", "/explanations");
  const html = Object.keys(explanations).sort().map((k) => `<section class="md">${marked.parse(explanations[k])}</section>`).join("");
  const box = $("debrief");
  box.innerHTML = `<h2>Debrief</h2>${html}`;
  box.querySelectorAll("pre > code.language-mermaid").forEach((code) => {
    const div = Object.assign(document.createElement("div"), { className: "mermaid", textContent: code.textContent });
    code.parentElement.replaceWith(div);
  });
  if (window.mermaid) { mermaid.initialize({ startOnLoad: false }); mermaid.run(); }
}

function start() {
  $("login").classList.add("hidden");
  $("game").classList.remove("hidden");
  refresh().catch(logout);
  clearInterval(timer);
  timer = setInterval(() => { if (!document.hidden && !document.activeElement.matches("input")) refresh().catch(() => {}); }, 30000);
}

function logout() {
  save(null);
  token = null;
  clearInterval(timer);
  location.reload();
}

$("login").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("loginErr").textContent = "";
  try {
    const res = await call("POST", "/join", { session: $("session").value.trim(), nick: $("nick").value.trim() });
    token = res.token;
    save(token);
    start();
  } catch (e) {
    $("loginErr").textContent = e.message;
  }
});
$("leave").onclick = logout;

const params = new URLSearchParams(location.search);
if (params.get("session")) $("session").value = params.get("session");
token = saved();
if (token) start();
