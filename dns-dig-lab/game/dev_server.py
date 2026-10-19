"""Run Dig Quest locally against a moto "AWS" server. Nothing touches real AWS.

    .venv/bin/python dev_server.py    # game: http://localhost:8787/?session=DEV
    admin token: dev
    DynamoDB viewer (live, auto-refresh):  http://localhost:8787/_debug
    (moto's own /moto-api/ dashboard lists items but not their attributes, hence this viewer)
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

import boto3
from moto.server import ThreadedMotoServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "backend"))
os.environ.update(AWS_DEFAULT_REGION="eu-west-3", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x", TABLE="quest", ADMIN_TOKEN="dev")
os.environ.setdefault("SECRET_DIR", os.path.join(HERE, "secret"))
PORT = int(os.environ.get("PORT", "8787"))
MOTO_PORT = int(os.environ.get("MOTO_PORT", "5000"))
os.environ["AWS_ENDPOINT_URL"] = f"http://127.0.0.1:{MOTO_PORT}"
FRONT = os.path.join(HERE, "frontend")
VIEWER = """<!doctype html><meta charset=utf-8><title>DynamoDB viewer</title>
<style>body{font:13px ui-monospace,monospace;margin:16px;background:#0b110d;color:#d4f5de}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #24372b;padding:4px 8px;vertical-align:top;text-align:left}
th{color:#3ddc84}tr.new td{background:#17321f}pre{margin:0;white-space:pre-wrap}</style>
<h2>table "quest" <small id=n></small></h2><table><thead><tr><th>PK<th>SK<th>attributes</thead><tbody id=b></tbody></table>
<script>let seen={};async function t(){const r=await (await fetch('/_debug/items')).json();n.textContent=r.length+' items';
b.innerHTML=r.map(i=>{const {PK,SK,...rest}=i;const k=PK+SK,j=JSON.stringify(rest,null,1);const c=seen[k]!==undefined&&seen[k]!==j?'new':'';seen[k]=j;
return `<tr class=${c}><td>${PK}<td>${SK}<td><pre>${j.replace(/</g,'&lt;')}</pre>`}).join('')}t();setInterval(t,2000)</script>"""
TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}


class Handler(BaseHTTPRequestHandler):
    def _api(self, method):
        import handler

        url = urlsplit(self.path)
        length = int(self.headers.get("content-length") or 0)
        event = {
            "requestContext": {"http": {"method": method}}, "rawPath": url.path, "headers": dict(self.headers),
            "queryStringParameters": dict(parse_qsl(url.query)), "body": self.rfile.read(length).decode() or None,
        }
        out = handler.lambda_handler(event)
        self._send(out["statusCode"], out["body"].encode(), "application/json")

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("content-type", ctype)
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-headers", "content-type,x-token,x-admin-token")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain")

    def do_POST(self):
        self._api("POST")

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in ("/state", "/leaderboard", "/explanations"):
            return self._api("GET")
        if url.path == "/_debug":
            return self._send(200, VIEWER.encode(), "text/html")
        if url.path == "/_debug/items":
            import store

            items = sorted((store.plain(i) for i in store.table().scan()["Items"]), key=lambda i: (i["PK"], i["SK"]))
            return self._send(200, json.dumps(items, default=str).encode(), "application/json")
        name = "index.html" if url.path == "/" else url.path.lstrip("/")
        path = os.path.normpath(os.path.join(FRONT, name))
        if not path.startswith(FRONT) or not os.path.isfile(path):
            return self._send(404, b"not found", "text/plain")
        with open(path, "rb") as fh:
            self._send(200, fh.read(), TYPES.get(os.path.splitext(path)[1], "application/octet-stream"))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    moto_server = ThreadedMotoServer(ip_address="127.0.0.1", port=MOTO_PORT, verbose=False)
    moto_server.start()
    try:
        boto3.client("dynamodb").create_table(
            TableName="quest", BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}, {"AttributeName": "SK", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        )
        import store

        store.create_session("DEV", "Local dev")
        print(f"game      http://localhost:{PORT}/?session=DEV")
        print(f"board     http://localhost:{PORT}/board.html?session=DEV")
        print(f"db viewer  http://localhost:{PORT}/_debug")
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        moto_server.stop()
