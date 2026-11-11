// Print the rendered deck to a 1280x720 PDF through Chromium's DevTools protocol.
// Plain --print-to-pdf ignores reveal's page size and clips the slides onto portrait pages.
// Usage: node print-pdf.mjs <chrome> <html file> <output pdf>
import { spawn } from "node:child_process";
import { once } from "node:events";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const RENDER_WAIT_MS = 8000;
const [chromePath, htmlFile, outputFile] = process.argv.slice(2);

const profileDir = mkdtempSync(join(tmpdir(), "print-pdf-"));
const chrome = spawn(chromePath, [
  "--headless=new",
  "--disable-gpu",
  "--remote-debugging-port=0",
  `--user-data-dir=${profileDir}`,
  "about:blank",
]);

const browserUrl = await new Promise((found, failed) => {
  chrome.stderr.on("data", (data) => {
    const match = String(data).match(/ws:\/\/\S+/);
    if (match) found(match[0]);
  });
  chrome.on("exit", () => failed(new Error("Chromium exited before opening its debugging port")));
});

const targets = await fetch(`http://${new URL(browserUrl).host}/json`).then((r) => r.json());
const socket = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
await new Promise((opened) => socket.addEventListener("open", opened));

let nextId = 0;
const pending = new Map();
socket.addEventListener("message", (event) => {
  const { id, result, error } = JSON.parse(event.data);
  if (!pending.has(id)) return;
  error ? pending.get(id).failed(new Error(error.message)) : pending.get(id).done(result);
  pending.delete(id);
});
const send = (method, params = {}) =>
  new Promise((done, failed) => {
    pending.set(++nextId, { done, failed });
    socket.send(JSON.stringify({ id: nextId, method, params }));
  });

try {
  await send("Page.enable");
  await send("Page.navigate", { url: `file://${resolve(htmlFile)}?print-pdf` });
  await new Promise((waited) => setTimeout(waited, RENDER_WAIT_MS));
  const { data } = await send("Page.printToPDF", {
    printBackground: true,
    preferCSSPageSize: false,
    paperWidth: 1280 / 96,
    paperHeight: 720 / 96,
    marginTop: 0,
    marginBottom: 0,
    marginLeft: 0,
    marginRight: 0,
  });
  writeFileSync(outputFile, Buffer.from(data, "base64"));
} finally {
  socket.close();
  const exited = once(chrome, "exit");
  chrome.kill();
  await exited;
  rmSync(profileDir, { recursive: true, force: true, maxRetries: 5 });
}
