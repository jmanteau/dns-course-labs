"use strict";
// The teacher's admin token: asked once per page load (or given as #token=… in the URL, never sent to the
// server), then kept in this tab only. A wrong or cancelled token never makes the page ask in a loop.
const AdminToken = (() => {
  let asked = false;

  function store(t) {
    try { if (t) sessionStorage.setItem("dq-admin", t); else sessionStorage.removeItem("dq-admin"); } catch (e) { /* storage blocked */ }
  }

  function get() {
    let t = null;
    try { t = sessionStorage.getItem("dq-admin"); } catch (e) { /* storage blocked */ }
    if (!t && !asked) {
      asked = true;
      t = prompt("Admin token (kept in this tab only)");
      store(t);
    }
    return t || "";
  }

  const fromHash = new URLSearchParams(location.hash.slice(1)).get("token");
  if (fromHash) {
    store(fromHash);
    history.replaceState(null, "", location.pathname + location.search);
  }

  // forget a rejected token; `again()` lets the next get() ask once more
  return { get, reject: () => store(null), again: () => { asked = false; } };
})();
