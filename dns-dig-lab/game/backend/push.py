"""WebSocket doorbell: tell every open page of a session that something changed, at once.

The message only says what changed ({"kind": "quiz" | "activities" | "session"}); pages then refetch
with the usual REST calls, so no data and no access rule lives here. Polling stays as a fallback.

On AWS, browsers connect to an API Gateway WebSocket API whose $connect/$disconnect reach handler.py,
which keeps one S#<code> | WS#<connectionId> item per open page. Locally, dev_server.py runs its own
WebSocket server and registers `local_hook` instead.
"""
import json
import os

import store

local_hook = None  # dev_server.py: fn(code, message) that broadcasts on the local WebSocket server
_client = None


def client():
    global _client
    if _client is None:
        import boto3

        _client = boto3.client("apigatewaymanagementapi", endpoint_url=os.environ["WS_CALLBACK"])
    return _client


def notify(code, kind):
    """Ring every page of the session. Never raises: a lost doorbell only means the next poll catches up."""
    message = json.dumps({"kind": kind})
    try:
        if local_hook:
            local_hook(code, message)
            return
        if not os.environ.get("WS_CALLBACK"):
            return
        for conn in store.list_connections(code):
            try:
                client().post_to_connection(ConnectionId=conn, Data=message.encode())
            except client().exceptions.GoneException:
                store.delete_connection(code, conn)
    except Exception as exc:  # noqa: BLE001  (the teacher's action must not fail because of a push)
        print(f"push to {code} failed: {exc}")
