#!/usr/bin/env python3
"""Teacher CLI for Dig Quest.

    python admin.py create CLASS-A "IUT Blagnac A"
    python admin.py close CLASS-A        # also unlocks every explanation
    python admin.py reopen CLASS-A

Needs QUEST_API (the ApiUrl output) and the admin token, either in QUEST_ADMIN_TOKEN
or read from Secrets Manager with QUEST_ADMIN_SECRET_ARN (the AdminSecretArn output).
"""
import json
import os
import sys
import urllib.error
import urllib.request


def admin_token():
    if os.environ.get("QUEST_ADMIN_TOKEN"):
        return os.environ["QUEST_ADMIN_TOKEN"]
    arn = os.environ.get("QUEST_ADMIN_SECRET_ARN")
    if not arn:
        sys.exit("set QUEST_ADMIN_TOKEN or QUEST_ADMIN_SECRET_ARN")
    import boto3

    return boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"]


def post(path, body):
    api = os.environ.get("QUEST_API") or sys.exit("set QUEST_API to the ApiUrl output")
    req = urllib.request.Request(
        api.rstrip("/") + path, data=json.dumps(body).encode(), method="POST",
        headers={"content-type": "application/json", "x-admin-token": admin_token()},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.exit(f"{exc.code}: {exc.read().decode()}")


def main(argv):
    if len(argv) >= 2 and argv[0] == "create":
        print(post("/admin/session", {"code": argv[1], "name": " ".join(argv[2:]) or argv[1]}))
    elif len(argv) == 2 and argv[0] in ("close", "reopen"):
        print(post(f"/admin/session/{argv[1]}/status", {"status": "open" if argv[0] == "reopen" else "closed"}))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
