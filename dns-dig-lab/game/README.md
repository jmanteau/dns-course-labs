# Dig Quest: the gamified correction

Students answer the lab questions in a browser, earn points, and see a live leaderboard.
The explanations (the old correction) unlock only once a student has cleared every part,
or when you close the session.

- Data questions are graded with a live DNS lookup, so answers never go stale.
- Hints cost 25% then 50% of a part; a wrong multiple-choice guess costs 25%.
- First to clear a mission gets +50, second +25, third +10.
- Players join with a class code and a nickname, no account.

## Layout

| Path | What |
|---|---|
| `backend/` | Lambda code: handler, checkers (dnspython), scoring, DynamoDB store |
| `frontend/` | Static player page (`index.html`) and projector board (`board.html`) |
| `infra/` | CDK app (Python): DynamoDB, Lambda, HTTP API, S3 + CloudFront, admin secret |
| `secret/` | **Private**: `questions.json` (answers, checks) and `explanations/*.md` |
| `tests/` | `pytest` (mocked DNS and DynamoDB); `pytest -m live` checks real DNS |
| `dev_server.py` | Run everything locally with in-memory DynamoDB |
| `admin.py` | Create and close class sessions |

## Keep the answers private

This repository is public, so `secret/` must live in a private repository:

```
git submodule add -f <private-repo-url> dns-dig-lab/game/secret
```

`secret/` is a git submodule (`jmanteau/dns-dig-lab-game`, private) and is copied into the Lambda package at deploy time.

## Try it locally

```
python3 -m venv .venv && .venv/bin/pip install dnspython "moto[server]" pytest boto3
.venv/bin/python dev_server.py     # http://localhost:8787/?session=DEV
                                   # board: /board.html?session=DEV
                                   # live DynamoDB viewer: /_debug
.venv/bin/python -m pytest         # unit tests
.venv/bin/python -m pytest -m live # before a class: are all live questions still answerable?
```

`dev_server.py` starts a moto "AWS" server (DynamoDB on port 5000) and runs the real Lambda handler against it,
so you can play as a student and watch the items change in the viewer. No Docker or AWS account needed.

## Deploy

```
cd infra
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
npx aws-cdk bootstrap          # once per account/region
npx aws-cdk deploy
```

The outputs give `GameUrl`, `BoardUrl`, `ApiUrl` and `AdminSecretArn`. Cost for a class is a few cents.

## Run a class

```
export QUEST_API=<ApiUrl> QUEST_ADMIN_SECRET_ARN=<AdminSecretArn>
python admin.py create CLASS-A "IUT Blagnac A"
```

Give students `<GameUrl>/?session=CLASS-A`, and project `<GameUrl>/board.html?session=CLASS-A`.
When the class ends: `python admin.py close CLASS-A` unlocks the explanations for everyone.

## Editing questions

Edit `secret/questions.json`. Part types: `live` (kinds `rrset`, `mx_primary`, `rcode`, `chain_len`,
`auth_ttl`, `txt_has`, `txt_count`), `static` (regex `patterns`) and `mcq` (`options`, `answer` index).
`txt_count` reads `backend/data/list100.txt`; keep it in sync with `../list100.txt`.
