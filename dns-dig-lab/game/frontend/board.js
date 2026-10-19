"use strict";
const API = window.QUEST_API;
const session = new URLSearchParams(location.search).get("session");
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let last = {};

async function tick() {
  if (!session) return;
  try {
    const res = await fetch(`${API}/leaderboard?session=${encodeURIComponent(session)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    document.getElementById("title").textContent = `Dig Quest · ${data.name}`;
    document.getElementById("meta").textContent = `${data.players.length} players · ${data.status === "closed" ? "session closed" : "join with code " + data.session}`;
    document.getElementById("rows").innerHTML = data.players.slice(0, 15).map((p, i) => {
      const changed = last[p.nick] !== undefined && last[p.nick] !== p.score;
      return `<div class="lrow ${changed ? "flash" : ""}"><span class="rank">#${i + 1}</span>
        <span class="name">${esc(p.nick)}<span class="bar"><i style="width:${(100 * p.solved) / data.totalParts}%"></i></span></span>
        <span class="sc">${p.score}</span></div>`;
    }).join("");
    last = Object.fromEntries(data.players.map((p) => [p.nick, p.score]));
    const medals = ["🥇", "🥈", "🥉"];
    document.getElementById("bloods").innerHTML = data.firstBloods
      .sort((a, b) => a.qid.localeCompare(b.qid) || a.rank - b.rank)
      .map((f) => `<span class="chip">🩸 ${esc(f.qid.toUpperCase())} ${medals[f.rank - 1]} ${esc(f.nick)}</span>`).join("");
  } catch (e) {
    document.getElementById("meta").textContent = `Cannot load the board: ${e.message}`;
  }
}
tick();
setInterval(tick, 5000);
