import json

import pytest

import handler
import push
import store
from test_handler import call, session  # noqa: F401  (fixtures)


def ws(kind, conn="c1", code=None):
    event = {"requestContext": {"connectionId": conn, "eventType": kind}}
    if code is not None:
        event["queryStringParameters"] = {"session": code}
    return handler.lambda_handler(event)["statusCode"]


def test_connect_and_disconnect(session):
    assert ws("CONNECT", code="nope") == 403
    assert ws("CONNECT", "c1", "cls1") == 200 and ws("CONNECT", "c2", "CLS1") == 200
    assert sorted(store.list_connections("CLS1")) == ["c1", "c2"]
    assert ws("MESSAGE", "c1") == 200  # messages from pages are ignored
    assert ws("DISCONNECT", "c1") == 200
    assert store.list_connections("CLS1") == ["c2"]


class FakeClient:
    class exceptions:
        class GoneException(Exception):
            pass

    def __init__(self, gone=()):
        self.sent, self.gone = [], set(gone)

    def post_to_connection(self, ConnectionId, Data):
        if ConnectionId in self.gone:
            raise self.exceptions.GoneException()
        self.sent.append((ConnectionId, json.loads(Data)))


def test_notify_rings_every_page_and_forgets_closed_ones(session, monkeypatch):
    ws("CONNECT", "c1", "CLS1")
    ws("CONNECT", "c2", "CLS1")
    fake = FakeClient(gone={"c2"})
    monkeypatch.setenv("WS_CALLBACK", "https://example.invalid/prod")
    monkeypatch.setattr(push, "_client", fake)
    push.notify("CLS1", "quiz")
    assert fake.sent == [("c1", {"kind": "quiz"})]
    assert store.list_connections("CLS1") == ["c1"]


def test_notify_never_raises(session, monkeypatch):
    monkeypatch.setenv("WS_CALLBACK", "https://example.invalid/prod")
    monkeypatch.setattr(store, "list_connections", lambda code: 1 / 0)
    push.notify("CLS1", "quiz")  # logged, not raised


@pytest.fixture
def rings(monkeypatch):
    out = []
    monkeypatch.setattr(push, "notify", lambda code, kind: out.append((code, kind)))
    return out


def test_teacher_actions_ring(session, rings):
    admin = {"admin": "adm"}
    call("POST", "/admin/quiz/CLS1", {"action": "open", "qid": "k1"}, **admin)
    call("POST", "/admin/quiz/CLS1", {"action": "reveal"}, **admin)
    call("POST", "/admin/quiz/CLS1", {"action": "close"}, **admin)
    call("POST", "/admin/session/CLS1/activities", {"dig": False}, **admin)
    call("POST", "/admin/session/CLS1/status", {"status": "closed"}, **admin)
    assert rings == [("CLS1", "quiz")] * 3 + [("CLS1", "activities"), ("CLS1", "session")]
