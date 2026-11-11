// Overwritten at deploy time by the CDK stack with the real API URL.
window.QUEST_API = window.QUEST_API || "http://localhost:8787";
// the WebSocket doorbell (dev_server.py serves it on port 8788)
window.QUEST_WS = window.QUEST_WS || `ws://${location.hostname}:8788`;
