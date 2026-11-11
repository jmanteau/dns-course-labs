"use strict";
// WebSocket doorbell: the server rings when the teacher changes something (quiz, activities, session);
// the page then refetches with its usual calls. Without a socket the pages simply keep polling.
const Live = (() => {
  let socket = null;
  let tries = 0;
  const state = { up: false };

  function connect(session, onRing) {
    if (!window.QUEST_WS || !session) return state;
    const open = () => {
      socket = new WebSocket(`${window.QUEST_WS}?session=${encodeURIComponent(session)}`);
      socket.onopen = () => { state.up = true; tries = 0; onRing({ kind: "hello" }); };  // catch up on anything missed
      socket.onmessage = (ev) => { try { onRing(JSON.parse(ev.data)); } catch (e) { /* not ours */ } };
      socket.onclose = () => {
        state.up = false;
        const wait = [1, 2, 5][tries] || 15;  // back off, then keep trying every 15 s
        tries += 1;
        setTimeout(open, wait * 1000);
      };
    };
    open();
    return state;
  }

  return { connect };
})();
