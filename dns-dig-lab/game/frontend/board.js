"use strict";
const API = window.QUEST_API;
const params = new URLSearchParams(location.search);
const session = params.get("session");
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const md = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
let last = {};
let lastAdv = {};
let lastQuiz = {};
let quiz = null;      // the latest /quiz/board answer
let ranking = null;   // the latest /leaderboard answer, for the side column during a question
let clock = 0;        // server time minus local time

// One ranking: the top 15, a progress bar per player (when there is a total), a flash when a score changes.
function rowsHtml(players, total, before) {
  return players.slice(0, 15).map((p, i) => {
    const changed = before[p.nick] !== undefined && before[p.nick] !== p.score;
    const bar = total ? `<span class="bar"><i style="width:${(100 * p.solved) / total}%"></i></span>` : "";
    return `<div class="lrow ${changed ? "flash" : ""}"><span class="rank">#${i + 1}</span>
      <span class="name">${esc(p.nick)}${bar}</span>
      <span class="sc">${p.score}</span></div>`;
  }).join("");
}

// Join QR code: this deployment's player page with the class code filled in.
function buildJoin() {
  if (!session || typeof qrcode !== "function") return;
  const url = new URL(`index.html?session=${encodeURIComponent(session)}`, location.href).href;
  const qr = qrcode(0, "M");
  qr.addData(url);
  qr.make();
  $("join").innerHTML = `${qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true })}<span>${esc(url)}</span>`;
}

async function boards() {
  const res = await fetch(`${API}/leaderboard?session=${encodeURIComponent(session)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  ranking = data;
  $("title").textContent = `Dig Quest · ${data.name}`;
  $("join").hidden = data.status === "closed";
  const a = data.activities || { dig: true, advanced: true };
  $("paused").hidden = a.dig && a.advanced;
  $("paused").textContent = !a.dig ? "⏸ Dig lab paused: wait for your teacher" : "⏸ Advanced missions paused";
  $("meta").textContent = `${data.players.length} players · ${data.status === "closed" ? "session closed" : "join with code " + data.session}`;
  $("rows").innerHTML = rowsHtml(data.players, data.totalParts, last);
  last = Object.fromEntries(data.players.map((p) => [p.nick, p.score]));
  const adv = data.advanced || [];
  const qz = data.quiz || [];
  $("advPanel").hidden = !adv.length;
  $("quizPanel").hidden = !qz.length;
  const panels = 1 + (adv.length ? 1 : 0) + (qz.length ? 1 : 0);
  $("boards").classList.toggle("two", panels === 2);
  $("boards").classList.toggle("three", panels === 3);
  $("advRows").innerHTML = rowsHtml(adv, data.advTotalParts, lastAdv);
  lastAdv = Object.fromEntries(adv.map((p) => [p.nick, p.score]));
  $("quizRows").innerHTML = rowsHtml(qz, 0, lastQuiz);
  lastQuiz = Object.fromEntries(qz.map((p) => [p.nick, p.score]));
  const medals = ["🥇", "🥈", "🥉"];
  $("bloods").innerHTML = data.firstBloods
    .sort((a, b) => a.qid.localeCompare(b.qid) || a.rank - b.rank)
    .map((f) => `<span class="chip">🩸 ${esc(f.qid.toUpperCase())} ${medals[f.rank - 1]} ${esc(f.nick)}</span>`).join("");
}

// ---- live quiz -------------------------------------------------------------------

const labels = (q) => (q.type === "static" ? ["right", "wrong"] : q.options);

function bars(q, live) {
  const right = q.type === "static" ? [0] : [].concat(q.answer ?? []);
  const counts = live.counts || [];
  return labels(q).map((label, k) => {
    const n = counts[k] || 0;
    const pct = live.answered ? Math.round((100 * n) / live.answered) : 0;
    return `<div class="qbar ${right.includes(k) ? "right" : ""}"><span>${right.includes(k) ? "✓ " : ""}${md(label)}</span><i style="width:${pct}%"></i><b>${n}</b></div>`;
  }).join("");
}

function quizHtml(live) {
  const q = live.question;
  const revealed = live.phase === "reveal";
  const head = `<p class="qmeta"><span>${live.answered} answer${live.answered === 1 ? "" : "s"}</span><span id="qClock"></span></p>
    <h1 class="qtext">${md(q.text)}</h1>`;
  const explain = revealed && q.explain ? `<p class="explain">${md(q.explain)}</p>` : "";
  if (!revealed) {
    if (q.type === "open" || q.type === "static") return `${head}<p class="sub">Type your answer on your phone.</p>`;
    return `${head}<ol class="qopts ${q.options.length > 8 ? "many" : ""}">${q.options.map((o) => `<li>${md(o)}</li>`).join("")}</ol>${q.type === "multi" ? '<p class="sub">Tick all that apply.</p>' : ""}`;
  }
  if (q.type === "open") {
    const wall = (live.wall || []).map((w) => `<div class="wall-row"><span>${esc(w.text)}</span><b>▲ ${w.votes}</b>
</div>`).join("");
    return `${head}${explain}<div class="wall big">${wall || '<p class="sub">No answers.</p>'}</div>`;
  }
  return `${head}<div class="qbars big ${labels(q).length > 8 ? "many" : ""}">${bars(q, live)}</div>${explain}`;
}

function clockTick() {
  const el = $("qClock");
  if (!el || !quiz || !quiz.live) return;
  if (quiz.live.phase !== "open") { el.textContent = "answer revealed"; return; }
  const left = Math.ceil(quiz.live.question.seconds - (Date.now() + clock - quiz.live.openedAt) / 1000);
  el.textContent = left > 0 ? `${left} s` : "time's up";
}

async function quizBoard() {
  const res = await fetch(`${API}/quiz/board?session=${encodeURIComponent(session)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  clock = data.now - Date.now();
  const changed = !quiz || JSON.stringify(data.live) !== JSON.stringify(quiz.live);
  quiz = data;
  $("quizView").hidden = !data.live;
  $("boardsView").hidden = !!data.live;
  if (data.live && changed) {
    $("quizView").innerHTML = `<div class="qmain">${quizHtml(data.live)}</div><aside class="qside" id="qside"></aside>`;
  }
  clockTick();
}

// Beside the question: the quiz ranking (it moves at each reveal) and how to join.
function sideHtml() {
  const side = $("qside");
  if (!side || !ranking) return;
  const rows = (ranking.quiz || []).slice(0, 10).map((p, i) => `<div class="srow"><span class="rank">#${i + 1}</span>
    <span class="name">${esc(p.nick)}</span><b>${p.score}</b></div>`).join("");
  side.innerHTML = `<h2>Quiz</h2>${rows || '<p class="sub">Points appear at each reveal.</p>'}
    <p class="sjoin">${ranking.players.length} players · join with code <b>${esc(ranking.session)}</b></p>`;
}

// Poll fast while a question is on screen (the answer count moves), slowly otherwise; the doorbell
// brings the teacher's actions at once, so the idle poll is only a safety net when it is up.
let live = { up: false };
let pending = null;

async function tick() {
  if (!session) return;
  try {
    await Promise.all([quizBoard(), boards()]);
    if (quiz.live) sideHtml();
  } catch (e) {
    $("meta").textContent = `Cannot load the board: ${e.message}`;
  }
}

async function loop() {
  clearTimeout(pending);
  await tick();
  pending = setTimeout(loop, quiz && quiz.live ? 1500 : live.up ? 10000 : 5000);
}
live = Live.connect(session, () => loop());
buildJoin();
loop();
setInterval(clockTick, 1000);
