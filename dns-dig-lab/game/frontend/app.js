"use strict";
const API = window.QUEST_API;
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// escaped text, with `backticks` shown as code and **stars** as bold
const md = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
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
  $("advScore").textContent = state.advScore;
  $("advScoreBox").classList.toggle("hidden", !state.mainDone);
  const adv = state.mainDone && state.advTotalParts ? ` · advanced ${state.advSolvedCount}/${state.advTotalParts}` : "";
  $("progress").textContent = `${state.solvedCount}/${state.totalParts} parts cleared${adv} · class ${state.session}${state.status === "closed" ? " (closed)" : ""}`;
  $("barFill").style.width = `${(100 * state.solvedCount) / state.totalParts}%`;
  const warm = state.questions.filter((q) => q.stage === "warmup");
  const main = state.questions.filter((q) => q.stage === "main");
  const advanced = state.questions.filter((q) => q.stage === "advanced");
  const act = state.activities || { dig: true, advanced: true };
  document.body.classList.toggle("lab-paused", !act.dig);
  if (!act.dig) {
    $("missions").innerHTML = `<article class="card waiting"><h2>⏸ Waiting for your teacher</h2>
      <p>The dig lab will start soon. Your progress is kept, and quiz questions still appear here.</p></article>`;
    $("debrief").classList.add("hidden");
    return;
  }
  const challenge = state.warmupDone ? "The challenge" : "🔒 The challenge: clear the warm-up to unlock it";
  const advTitle = !state.mainDone
    ? "🔒 Advanced: clear every mission to unlock it"
    : !act.advanced
      ? "⏸ Advanced: your teacher opens them"
      : `Advanced: separate leaderboard. Read the <a href="deck/dns-advanced.html" target="_blank" rel="noopener">DNS Beyond the Basics</a> slides first`;
  $("missions").innerHTML = (warm.length ? `<h2 class="stage-title">Warm-up: use dig in your own terminal</h2>${warm.map((q, i) => missionHtml(q, `Warm-up ${i + 1}`)).join("")}<h2 class="stage-title">${challenge}</h2>` : "")
    + main.map((q, i) => missionHtml(q, `Mission ${i + 1}`)).join("")
    + (advanced.length ? `<h2 class="stage-title">${advTitle}</h2>${advanced.map((q, i) => missionHtml(q, `Advanced ${i + 1}`)).join("")}` : "");
  document.body.classList.toggle("warmup", !state.warmupDone);
  $("dig").classList.toggle("locked", !state.warmupDone);
  const debrief = $("debrief");
  debrief.classList.toggle("hidden", !state.unlocked);
  // the debrief is rebuilt when the advanced explanations unlock too
  const level = `${state.unlocked}|${state.advUnlocked}`;
  if (state.unlocked && debrief.dataset.ready !== level) {
    debrief.dataset.ready = level;
    debrief.innerHTML = `<h2>${state.status === "closed" ? "Session closed" : "All missions cleared"}</h2>
      <p class="sub">${state.advUnlocked ? "All the explanations are unlocked, advanced ones included." : "The explanations of the missions are unlocked."}</p><button id="showDebrief">Read the debrief</button>`;
    $("showDebrief").onclick = loadDebrief;
  }
}

function missionHtml(q, label) {
  if (q.locked === "paused") return "";
  if (q.locked) return `<article class="card locked"><h2>🔒 ${label}: ${esc(q.title)}</h2></article>`;
  const done = q.parts.every((p) => p.solved != null);
  const parts = q.parts.map((p) => partHtml(q, p)).join("");
  return `<article class="card ${done ? "done" : ""}"><h2>${done ? "✓ " : ""}${label}: ${esc(q.title)}</h2>
    <p class="prompt">${md(q.prompt)}</p>${parts}</article>`;
}

function partHtml(q, p) {
  const id = `${q.id}-${p.id}`;
  const head = `<div class="part-head"><span>${md(p.label)}</span><span class="pts">${p.solved != null ? `+${p.solved}` : `${p.points} pts`}</span></div>`;
  if (p.solved != null) return `<div class="part">${head}<span class="ok">✓ solved</span></div>`;
  const hints = p.hints.map((h) => `<div class="hint">💡 ${md(h)}</div>`).join("");
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
    const wasWarm = state.warmupDone;
    const wasAdv = state.advUnlocked;
    const wasMain = state.mainDone;
    await refresh();
    if (!wasWarm && state.warmupDone) toast("Warm-up cleared: the challenge and the dig console are unlocked");
    if (!wasMain && state.mainDone && state.advTotalParts) toast("Every mission cleared: the advanced missions are open");
    if ((!wasUnlocked && state.unlocked) || (!wasWarm && state.warmupDone) || (!wasAdv && state.advUnlocked)) confetti();
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

// ---- live quiz -------------------------------------------------------------------
// The teacher opens one question at a time; this card polls for it every 3 s.

let quizTimer = null;
let live = { up: false };  // the WebSocket doorbell (live.js)
let lastQuizPoll = 0;
let quizKey = "";      // what the card shows: re-rendered only when it changes, so typing is never lost
let quizClock = 0;     // server time minus local time, so a wrong phone clock does not skew the countdown
let quizLive = null;

function quizBars(q, counts, answered) {
  const labels = q.type === "static" ? ["right", "wrong"] : q.options;
  const right = q.type === "static" ? [0] : [].concat(q.answer ?? []);
  return `<div class="qbars ${labels.length > 8 ? "many" : ""}">${labels.map((label, k) => {
    const n = counts[k] || 0;
    const pct = answered ? Math.round((100 * n) / answered) : 0;
    return `<div class="qbar ${right.includes(k) ? "right" : ""}"><span>${right.includes(k) ? "✓ " : ""}${md(label)}</span>
      <i style="width:${pct}%"></i><b>${n}</b></div>`;
  }).join("")}</div>`;
}

function quizHtml(live) {
  const q = live.question;
  const head = `<div class="quiz-top"><span>Quiz</span><span class="pts" id="quizClock"></span></div><h2 class="quiz-q">${md(q.text)}</h2>`;
  if (live.phase === "open") {
    if (live.mine) return `${head}<p class="ok">✓ Answer saved. Wait for the reveal.</p>`;
    if (q.type === "mcq" || q.type === "poll") {
      return `${head}<div class="opts">${q.options.map((o, k) => `<button class="opt" data-qopt="${k}">${md(o)}</button>`).join("")}</div><p class="err" id="quizErr" role="alert"></p>`;
    }
    if (q.type === "multi") {
      return `${head}<p class="sub">Tick all that apply.</p><form id="quizMulti" class="qmulti ${q.options.length > 8 ? "many" : ""}">${q.options.map((o, k) => `<label><input type="checkbox" value="${k}"> ${md(o)}</label>`).join("")}<button>Send</button></form><p class="err" id="quizErr" role="alert"></p>`;
    }
    const max = q.type === "open" ? 200 : 60;
    return `${head}<form id="quizText" class="row"><input type="text" maxlength="${max}" aria-label="Your answer" autocomplete="off" spellcheck="false"><button>Send</button></form><p class="err" id="quizErr" role="alert"></p>`;
  }
  // revealed
  let verdict = "";
  if (live.mine && live.mine.correct === true) verdict = `<p class="ok">✓ Right: +${live.mine.points} quiz points</p>`;
  else if (live.mine && live.mine.correct === false) verdict = `<p class="bad">✗ Not this time.</p>`;
  else if (!live.mine) verdict = `<p class="sub">You did not answer this one.</p>`;
  const explain = q.explain ? `<p class="explain">${md(q.explain)}</p>` : "";
  if (q.type === "open") {
    const wall = (live.wall || []).map((w) => `<div class="wall-row"><span>${esc(w.text)}</span>
      ${w.mine ? `<span class="sub">yours · ${w.votes}</span>` : `<button class="ghost ${w.votedByMe ? "voted" : ""}" data-vote="${w.id}" ${w.votedByMe ? "disabled" : ""}>▲ ${w.votes}</button>`}</div>`).join("");
    return `${head}${explain}<p class="sub">Upvote the best answers.</p><div class="wall">${wall || '<p class="sub">No answers.</p>'}</div>`;
  }
  return `${head}${verdict}${explain}${quizBars(q, live.counts || [], live.answered)}`;
}

function quizTick() {
  const el = $("quizClock");
  if (!el || !quizLive) return;
  if (quizLive.phase !== "open") { el.textContent = ""; return; }
  const left = Math.ceil(quizLive.question.seconds - (Date.now() + quizClock - quizLive.openedAt) / 1000);
  el.textContent = left > 0 ? `${left} s` : "time's up";
}

async function quizPoll() {
  if (!token || document.hidden) return;
  lastQuizPoll = Date.now();
  let data;
  try { data = await call("GET", "/quiz"); } catch (e) { return; }
  quizClock = data.now - Date.now();
  quizLive = data.live;
  // a teacher's switch shows up at the quiz's pace, without waiting for the 30 s refresh
  if (state && JSON.stringify(data.activities) !== JSON.stringify(state.activities)) refresh().catch(() => {});
  $("quizScore").textContent = data.quizScore;
  $("quizScoreBox").classList.toggle("hidden", !data.quizScore);
  const box = $("quiz");
  box.classList.toggle("hidden", !data.live);
  document.body.classList.toggle("quiz-on", !!data.live);  // the question fills the screen
  if (!data.live) { quizKey = ""; box.innerHTML = ""; return; }
  const key = JSON.stringify([data.live.question.id, data.live.phase, !!data.live.mine, data.live.wall, data.live.counts]);
  if (key !== quizKey) {
    quizKey = key;
    box.innerHTML = quizHtml(data.live);
  }
  quizTick();
}

async function quizSend(value) {
  try {
    await call("POST", "/quiz/answer", { qid: quizLive.question.id, value });
  } catch (e) {
    const err = $("quizErr");
    if (err) err.textContent = e.message;
  }
  quizPoll();
}

$("quiz").addEventListener("click", async (ev) => {
  const opt = ev.target.closest("[data-qopt]");
  if (opt) return quizSend(Number(opt.dataset.qopt));
  const vote = ev.target.closest("[data-vote]");
  if (vote) {
    vote.disabled = true;
    try { await call("POST", "/quiz/vote", { qid: quizLive.question.id, id: vote.dataset.vote }); } catch (e) { toast(e.message); }
    quizPoll();
  }
});
$("quiz").addEventListener("submit", (ev) => {
  ev.preventDefault();
  if (ev.target.id === "quizMulti") {
    quizSend([...ev.target.querySelectorAll("input:checked")].map((i) => Number(i.value)));
  } else if (ev.target.id === "quizText") {
    quizSend(ev.target.querySelector("input").value);
  }
});
setInterval(quizTick, 1000);

// ---- dig console ---------------------------------------------------------------

const DIG_OPTS = ["Short", "Trace", "Norecurse", "Dnssec", "Tcp", "Nsid", "Cd"];
const HOST_RE = /\b([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+\.)/g;

function digForm() {
  const server = $("digServer").value;
  const body = {
    names: $("digNames").value, type: $("digType").value, class: $("digClass").value, subnet: $("digSubnet").value.trim(),
    port: $("digPort").value.trim(),
    server: server === "ip" ? $("digIp").value.trim() : server,
  };
  DIG_OPTS.forEach((o) => { body[o.toLowerCase()] = $(`dig${o}`).checked; });
  return body;
}

function saveDigForm() {
  const f = { ...digForm(), server: $("digServer").value, ip: $("digIp").value };
  try { localStorage.setItem("dq-dig", JSON.stringify(f)); } catch (e) { /* private mode */ }
}

function restoreDigForm() {
  let f = null;
  try { f = JSON.parse(localStorage.getItem("dq-dig")); } catch (e) { /* none saved */ }
  if (!f) return;
  $("digNames").value = f.names || "";
  $("digType").value = f.type || "A";
  $("digClass").value = f.class || "IN";
  $("digServer").value = f.server || "google";
  $("digIp").value = f.ip || "";
  $("digSubnet").value = f.subnet || "";
  $("digPort").value = f.port || "";
  DIG_OPTS.forEach((o) => { $(`dig${o}`).checked = !!f[o.toLowerCase()]; });
}

// Colour one line of output: comments dim, TTL gold, type accent, hostnames clickable.
function digLine(line) {
  const host = (t) => t.replace(HOST_RE, '<span class="host">$1</span>');
  const e = esc(line);
  if (e.startsWith(";")) return `<span class="c">${e}</span>`;
  const m = e.match(/^(\S+)(\s+)(\d+)(\s+(?:IN|CH)\s+)(\S+)(\s+)(.*)$/);
  if (!m) return host(e);
  return `${host(m[1])}${m[2]}<span class="ttl">${m[3]}</span>${m[4]}<span class="ty">${m[5]}</span>${m[6]}${host(m[7])}`;
}

function showDig(res) {
  const out = $("digOut");
  const box = document.createElement("details");
  box.className = "dig-res";
  box.open = true;
  box.innerHTML = `<summary><code>❯ ${esc(res.command)}</code><button type="button" class="ghost" data-copy>copy</button></summary>
    <pre>${res.output.split("\n").map(digLine).join("\n")}</pre>`;
  box.querySelector("[data-copy]").dataset.copy = res.command;
  out.prepend(box);
  [...out.children].slice(10).forEach((el) => el.remove());
}

async function runDig(ev) {
  ev.preventDefault();
  saveDigForm();
  $("digErr").textContent = "";
  $("digGo").disabled = true;
  $("digGo").textContent = "…";
  try {
    showDig(await call("POST", "/dig", digForm()));
  } catch (e) {
    $("digErr").textContent = e.message;
  } finally {
    $("digGo").disabled = false;
    $("digGo").textContent = "Dig";
  }
}

function toggleDig(open) {
  $("dig").classList.toggle("open", open);
  if (open) $("digNames").focus();
}

$("digForm").addEventListener("submit", runDig);
$("digForm").addEventListener("keydown", (ev) => { if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) runDig(ev); });
$("digServer").addEventListener("change", () => $("digIp").classList.toggle("hidden", $("digServer").value !== "ip"));
$("digClear").onclick = () => { $("digOut").innerHTML = ""; $("digErr").textContent = ""; };
$("digToggle").onclick = () => toggleDig(true);
$("digClose").onclick = () => toggleDig(false);
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") toggleDig(false); });
$("digOut").addEventListener("click", (ev) => {
  const copy = ev.target.closest("[data-copy]");
  if (copy) {
    ev.preventDefault();
    navigator.clipboard?.writeText(copy.dataset.copy).then(() => { copy.textContent = "copied"; setTimeout(() => { copy.textContent = "copy"; }, 1200); });
    return;
  }
  const host = ev.target.closest(".host");
  if (host) {
    $("digNames").value = host.textContent.replace(/\.$/, "");
    $("digNames").focus();
  }
});
restoreDigForm();
$("digIp").classList.toggle("hidden", $("digServer").value !== "ip");

function start() {
  document.body.classList.add("playing");
  $("login").classList.add("hidden");
  $("game").classList.remove("hidden");
  refresh().catch(logout);
  clearInterval(timer);
  timer = setInterval(() => { if (!document.hidden && !document.activeElement.matches("input")) refresh().catch(() => {}); }, 30000);
  clearInterval(quizTimer);
  quizPoll();
  // with the doorbell up, the teacher's actions arrive at once: poll only every 20 s, as a safety net
  quizTimer = setInterval(() => { if (!live.up || Date.now() - lastQuizPoll > 20000) quizPoll(); }, 3000);
  live = Live.connect(token.split(":")[0], (msg) => {
    quizPoll();
    if (msg.kind === "activities" || msg.kind === "session") refresh().catch(() => {});
  });
}

function logout() {
  save(null);
  token = null;
  clearInterval(timer);
  clearInterval(quizTimer);
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
