"use strict";
// The teacher's page: session, activity switches and the live quiz. The projected board shows none of this.
const API = window.QUEST_API;
const session = new URLSearchParams(location.search).get("session");
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const md = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
let quiz = null;   // the latest /quiz/board answer (with the rounds: admin header)
let board = null;  // the latest /leaderboard answer (players, status, activities)
let clock = 0;     // server time minus local time

async function api(method, path, body) {
  const res = await fetch(API + path, {
    method,
    headers: { "content-type": "application/json", "x-admin-token": AdminToken.get() },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || `HTTP ${res.status}`), { status: res.status });
  return data;
}

async function act(method, path, body) {
  $("err").textContent = "";
  try { await api(method, path, body); } catch (e) { $("err").textContent = e.message; }
  await load().catch(() => {});
}

// ---- rendering -------------------------------------------------------------------

function renderSession() {
  const open = board.status === "open";
  $("title").textContent = `Dig Quest · ${board.name}`;
  $("meta").textContent = `class code ${board.session} · ${board.players.length} players`;
  $("sessionInfo").innerHTML = open ? "Open: students can join and play." : "Closed: every explanation is unlocked, nobody can join.";
  $("sessionToggle").textContent = open ? "Close the session" : "Reopen the session";
  const a = board.activities;
  $("actDig").checked = a.dig;
  $("actAdvanced").checked = a.advanced;
  $("actDigState").textContent = a.dig ? "running" : "paused";
  $("actAdvancedState").textContent = a.advanced ? "running" : "paused";
}

function bars(q, live) {
  const labels = q.type === "static" ? ["right", "wrong"] : q.options;
  const right = q.type === "static" ? [0] : [].concat(q.answer ?? []);
  return labels.map((label, k) => {
    const n = (live.counts || [])[k] || 0;
    const pct = live.answered ? Math.round((100 * n) / live.answered) : 0;
    return `<div class="qbar ${right.includes(k) ? "right" : ""}"><span>${right.includes(k) ? "✓ " : ""}${md(label)}</span><i style="width:${pct}%"></i><b>${n}</b></div>`;
  }).join("");
}

function renderQuiz() {
  const sel = $("round");
  if (!sel.options.length) {
    sel.innerHTML = quiz.rounds.map((r) => `<option value="${r.id}">${esc(r.title)}</option>`).join("");
    if (quiz.live) sel.value = quiz.live.question.round;
  }
  const round = currentRound();
  const live = quiz.live;
  $("qlist").innerHTML = round.questions.map((q, i) => `<button class="ghost ${live && q.id === live.question.id ? "live" : ""}" data-open="${q.id}" title="${esc(q.text)}">${i + 1}</button>`).join("");
  $("qReveal").disabled = !(live && live.phase === "open");
  $("qClose").disabled = !live;
  if (!live) { $("qPreview").innerHTML = '<p class="sub">No question on screen.</p>'; return; }
  const q = live.question;
  const players = board ? board.players.length : 0;
  let body = "";
  if (live.phase === "open") {
    body = q.options ? `<ol class="qopts small ${q.options.length > 8 ? "many" : ""}">${q.options.map((o) => `<li>${md(o)}</li>`).join("")}</ol>` : "";
  } else if (q.type === "open") {
    body = (live.wall || []).map((w) => `<div class="wall-row"><span>${esc(w.text)}</span><b>▲ ${w.votes}</b><button class="ghost" data-hide="${w.id}" title="Hide this answer">✕</button></div>`).join("") || '<p class="sub">No answers.</p>';
    body = `<div class="wall">${body}</div>`;
  } else {
    body = `<div class="qbars ${(q.options || []).length > 8 ? "many" : ""}">${bars(q, live)}</div>`;
  }
  $("qPreview").innerHTML = `<p class="qmeta"><span>${live.answered} of ${players} answered</span><span id="qClock"></span></p>
    <h3>${md(q.text)}</h3>${body}${live.phase === "reveal" && q.explain ? `<p class="explain">${md(q.explain)}</p>` : ""}`;
  clockTick();
}

function currentRound() {
  return quiz.rounds.find((r) => String(r.id) === $("round").value) || quiz.rounds[0];
}

function clockTick() {
  const el = $("qClock");
  if (!el || !quiz || !quiz.live) return;
  if (quiz.live.phase !== "open") { el.textContent = "answer revealed"; return; }
  const left = Math.ceil(quiz.live.question.seconds - (Date.now() + clock - quiz.live.openedAt) / 1000);
  el.textContent = left > 0 ? `${left} s` : "time's up";
}

async function load() {
  const [q, b] = await Promise.all([
    api("GET", `/quiz/board?session=${encodeURIComponent(session)}`),
    api("GET", `/leaderboard?session=${encodeURIComponent(session)}`),
  ]);
  clock = q.now - Date.now();
  if (!q.rounds) {
    AdminToken.reject();
    $("panels").hidden = true;
    $("tokenAsk").hidden = false;
    $("err").textContent = "No valid admin token: the controls stay locked.";
    return;
  }
  $("tokenAsk").hidden = true;
  $("panels").hidden = false;
  const changed = !quiz || JSON.stringify(q.live) !== JSON.stringify(quiz.live) || !board || board.players.length !== b.players.length;
  quiz = q;
  board = b;
  renderSession();
  if (changed) renderQuiz();
}

// ---- actions ---------------------------------------------------------------------

// Points are added at the reveal: leaving a question before it loses them, so ask first.
function leaveUnrevealed(what) {
  if (!quiz.live || quiz.live.phase !== "open") return true;
  return confirm(`The current question has not been revealed: its ${quiz.live.answered} answer(s) will score no points.\n\n${what} anyway?`);
}

function openQuestion(qid) {
  if (leaveUnrevealed("Open the next question")) act("POST", `/admin/quiz/${session}`, { action: "open", qid });
}

function closeQuestion() {
  if (leaveUnrevealed("Close it")) act("POST", `/admin/quiz/${session}`, { action: "close" });
}

function openNext() {
  const ids = currentRound().questions.map((q) => q.id);
  const at = quiz.live ? ids.indexOf(quiz.live.question.id) : -1;
  if (at + 1 < ids.length) openQuestion(ids[at + 1]);
  else $("err").textContent = "End of the round: pick the next one.";
}

$("tokenAsk").onclick = () => { AdminToken.again(); $("err").textContent = ""; load().catch((e) => { $("err").textContent = e.message; }); };
$("sessionToggle").onclick = () => act("POST", `/admin/session/${session}/status`, { status: board.status === "open" ? "closed" : "open" });
$("actDig").onchange = (ev) => act("POST", `/admin/session/${session}/activities`, { dig: ev.target.checked });
$("actAdvanced").onchange = (ev) => act("POST", `/admin/session/${session}/activities`, { advanced: ev.target.checked });
$("round").onchange = () => renderQuiz();
$("qNext").onclick = openNext;
$("qReveal").onclick = () => act("POST", `/admin/quiz/${session}`, { action: "reveal" });
$("qClose").onclick = closeQuestion;
$("qlist").addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-open]");
  if (b) openQuestion(b.dataset.open);
});
$("qPreview").addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-hide]");
  if (b) act("POST", `/admin/quiz/${session}`, { action: "hide", qid: quiz.live.question.id, id: b.dataset.hide });
});
// a presentation clicker sends arrow or page keys
document.addEventListener("keydown", (ev) => {
  if (!quiz || !quiz.rounds || ev.target.matches("input, select")) return;
  if (ev.key === "ArrowRight" || ev.key === "PageDown") openNext();
  else if (ev.key === "r" || ev.key === "R") act("POST", `/admin/quiz/${session}`, { action: "reveal" });
  else if (ev.key === "Escape") closeQuestion();
});

if (session) {
  const code = encodeURIComponent(session);
  $("boardFrame").src = `board.html?session=${code}`;
  $("links").innerHTML = `Projector: <a href="board.html?session=${code}" target="_blank" rel="noopener">board</a> · Students: <a href="index.html?session=${code}" target="_blank" rel="noopener">player page</a>`;
}

// Poll fast while a question is on screen (the answer count moves), slowly otherwise; the doorbell
// brings changes at once, so the idle poll is only a safety net when it is up.
let live = { up: false };
let pending = null;

async function loop() {
  clearTimeout(pending);
  if (session) {
    try { await load(); } catch (e) { $("err").textContent = `Cannot load: ${e.message}`; }
  }
  pending = setTimeout(loop, quiz && quiz.live ? 1500 : live.up ? 10000 : 5000);
}
live = Live.connect(session, () => loop());
loop();
setInterval(clockTick, 1000);
