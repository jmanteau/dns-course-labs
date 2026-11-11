"use strict";
const API = window.QUEST_API;
const session = new URLSearchParams(location.search).get("session");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let last = {};
let lastAdv = {};

// One ranking: the top 15, a progress bar per player, a flash when a score changes.
function rowsHtml(players, total, before) {
  return players.slice(0, 15).map((p, i) => {
    const changed = before[p.nick] !== undefined && before[p.nick] !== p.score;
    return `<div class="lrow ${changed ? "flash" : ""}"><span class="rank">#${i + 1}</span>
      <span class="name">${esc(p.nick)}<span class="bar"><i style="width:${total ? (100 * p.solved) / total : 0}%"></i></span></span>
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
  document.getElementById("join").innerHTML = `${qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true })}<span>${esc(url)}</span>`;
}

async function tick() {
  if (!session) return;
  try {
    const res = await fetch(`${API}/leaderboard?session=${encodeURIComponent(session)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    document.getElementById("title").textContent = `Dig Quest · ${data.name}`;
    document.getElementById("join").hidden = data.status === "closed";
    document.getElementById("meta").textContent = `${data.players.length} players · ${data.status === "closed" ? "session closed" : "join with code " + data.session}`;
    document.getElementById("rows").innerHTML = rowsHtml(data.players, data.totalParts, last);
    last = Object.fromEntries(data.players.map((p) => [p.nick, p.score]));
    const adv = data.advanced || [];
    document.getElementById("advPanel").hidden = !adv.length;
    document.getElementById("boards").classList.toggle("two", adv.length > 0);
    document.getElementById("advRows").innerHTML = rowsHtml(adv, data.advTotalParts, lastAdv);
    lastAdv = Object.fromEntries(adv.map((p) => [p.nick, p.score]));
    const medals = ["🥇", "🥈", "🥉"];
    document.getElementById("bloods").innerHTML = data.firstBloods
      .sort((a, b) => a.qid.localeCompare(b.qid) || a.rank - b.rank)
      .map((f) => `<span class="chip">🩸 ${esc(f.qid.toUpperCase())} ${medals[f.rank - 1]} ${esc(f.nick)}</span>`).join("");
  } catch (e) {
    document.getElementById("meta").textContent = `Cannot load the board: ${e.message}`;
  }
}
buildJoin();
tick();
setInterval(tick, 5000);
