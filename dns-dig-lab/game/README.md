# Dig Quest: the gamified correction

Students answer the lab questions in a browser, earn points, and see a live leaderboard.
The explanations (the old correction) unlock only once a student has cleared every part,
or when you close the session.

- Data questions are graded with a live DNS lookup, so answers never go stale.
- Hints cost 25% then 50% of a part; a wrong multiple-choice guess costs 25%.
- First to clear a mission gets +50, second +25, third +10.
- Players join with a class code and a nickname, no account.
- A warm-up comes first: five short questions answered with `dig` on the student's own machine (`dig -v`, their resolver's IP, a first lookup, NXDOMAIN and flags, writing a command). The missions and the dig console stay locked until it is cleared. No first-blood bonus on the warm-up.
- An **advanced** stage opens once every main mission is solved: 14 missions on concepts the main course does not teach (anycast and CHAOS, NSID, whoami resolvers, SOA, extended errors, DNSSEC chain, mail records, IPv6 reverse, IDN, truncation, SRV/NAPTR, AXFR and NSEC walking). Its points go to a **separate leaderboard**, shown beside the main one on the board, so the main ranking stays fair. Its explanations unlock when every advanced part is solved, or when the session closes.
- The theory for the advanced stage is the *DNS Beyond the Basics* deck (`course/dns-advanced.qmd`). The game links to it as `deck/dns-advanced.html`: build it first with `make single DECK=dns-advanced` in `course/`, and the deploy and `dev_server.py` pick it up.
- A dig console sits beside the missions (a drawer on phones): it runs real lookups (`+short`, `+trace`, `+norecurse`, `+dnssec`, `+tcp`, `+nsid`, `+cd`, `+subnet`, `-x`, class `CH`, authoritative server) and shows the `dig` command that matches. Extended DNS Errors and NSID are printed like dig does. Public servers only (a server name must resolve to a public address), 20 lookups a minute per player. AXFR and `-p` work only toward the game server (`GAME_SERVER`, set by the stack), so the console cannot transfer or scan anyone else's servers.

## Layout

| Path | What |
|---|---|
| `backend/` | Lambda code: handler, checkers (dnspython), dig console (`dig.py`), scoring, DynamoDB store |
| `frontend/` | Static player page (`index.html`) and projector board (`board.html`, with a join QR code from the vendored `qrcode.min.js`) |
| `infra/` | CDK app (Python): DynamoDB, Lambda, HTTP API, S3 + CloudFront, admin secret |
| `secret/` | **Private**: `questions.json` (answers, checks) and `explanations/*.md` |
| `tests/` | `pytest` (mocked DNS and DynamoDB); `pytest -m live` checks real DNS |
| `dev_server.py` | Run everything locally with in-memory DynamoDB |
| `admin.py` | Create and close class sessions |
| `Makefile` | Shortcuts for the commands below: `make help` |

## Keep the answers private

This repository is public, so `secret/` must live in a private repository:

```
git submodule add -f <private-repo-url> dns-dig-lab/game/secret
```

`secret/` is a git submodule (`jmanteau/dns-dig-lab-game`, private) and is copied into the Lambda package at deploy time.

## Try it locally

`make help` lists the shortcuts for everything below (`make setup`, `dev`, `test`, `live`, `zone-check`, `sim-test`, `deploy`, `session`, `close`). `make dev` and `make deploy` build the advanced slides first.

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
npx aws-cdk deploy --all
```

The outputs give `GameUrl`, `BoardUrl`, `ApiUrl` and `AdminSecretArn`. Cost for a class is a few cents.

`--all` also deploys `DigQuestZone`, the game zone (below), when `secret/zone.json` exists.

## The game zone

Missions a15 to a20 are played on a real zone, `quest.jmanteau.fr`: a trail of clues (TXT → MX → SRV), a CNAME maze, wildcards, encoded TXT records, a long TXT and a picture split into TXT chunks.

- `secret/zone.json` (private) holds the content, so the answers stay out of this repository. `infra/game_zone.py` turns it into Route 53 records; its docstring describes the spec.
- `DigQuestZone` creates the hosted zone and, since `jmanteau.fr` is in the same account (`"parent"` in the spec), the NS delegation too. It costs $0.50 a month plus queries.
- After a deploy or an edit of the spec: `pytest -m live -k "game_zone or wildcard"` checks that every record is published as the spec describes (allow the 300 s TTL for changes).

## The game server

Missions a21 to a25 need what Route 53 cannot do, so BIND 9.20 runs in Docker on an always-on host (`oraclevm`, an Oracle Cloud free-tier Ampere VM) as `ns.quest.jmanteau.fr`: an open zone transfer (`axfr.`), a zone signed with NSEC to walk (`walk.`), custom CH TXT answers, a second instance on port 8053, and `secret.lab`, a zone no resolver can find.

- `secret/server.json` (private) holds the content and the server's reserved public IPv4 (`address`). `infra/game_server.py` renders a Docker folder from it: a Debian 13 image, two containers on the host network (so BIND sees real client addresses for its rate limiting), `named.conf` and the zone files.
- `DigQuestZone` publishes the server's address and delegates `axfr.` and `walk.` to it.
- Authoritative only (`recursion no`), with response rate limiting: it can never serve as an open resolver.
- First time: add `oraclevm` to `~/.ssh/config`, install Docker with the compose plugin on the VM, allow UDP and TCP 53 and 8053 in the VCN security list (Oracle console), then `make server-firewall` for the host firewall.
- Each change of the spec: `make server-deploy` (copies the folder over SSH, then `docker compose up -d --build`), `make deploy-zone` if the address or the zones changed, then `make server-check`, which checks the CH answers, the transfer, the NSEC chain, the private zone and the second port against the spec. `make server-logs` shows the containers' logs.

## Local simulation

Test the game zone and the game server before deploying anything, or after editing a spec: `make sim-test`. It needs Docker or Podman. `infra/sim.py` renders `build/sim/` from the same specs that get deployed, then compose starts these containers on a private network (10.53.0.0/24):

| container | address | plays |
|-----------|---------|-------|
| `resolver` | 10.53.0.2 | the resolver students use: the Internet through 8.8.8.8, and the local game zone, delegations included |
| `zone` | 10.53.0.10 | Route 53: the game zone, served by BIND (TXT escapes converted from octal to decimal) |
| `main` + `alt` | 10.53.0.53 | the game server, on ports 53 and 8053, exactly as on `oraclevm` |
| `runner` | 10.53.0.100 | the game code: the tests, or `dev_server.py` |

The tests run inside `runner`, because on macOS the host cannot reach those addresses. `make sim-test` runs the unit tests first, then every `live` test plus the end-to-end tests in `tests/test_sim.py`: grading of a15, a23, a24 and a25, and the console's CH, AXFR and `-p 8053`.

`make sim-dev` serves the game on http://localhost:8787/?session=DEV against the simulation. `make sim-down` stops and removes the containers.

How the code is pointed at the simulation (none of these variables is set in AWS):
- `QUEST_RESOLVER` replaces 8.8.8.8 in the checkers and the console;
- `DIG_ALLOW_NET` lets the console reach that private network;
- `GAME_SERVER` names the game server.

The limit: `+trace` starts from the real root servers, so it cannot find the local game zone.

## Run a class

```
export QUEST_API=<ApiUrl> QUEST_ADMIN_SECRET_ARN=<AdminSecretArn>
python admin.py create CLASS-A "IUT Blagnac A"
```

Project `<GameUrl>/board.html?session=CLASS-A`: it shows a QR code that opens `<GameUrl>/index.html?session=CLASS-A` with the class code filled in (hidden once the session is closed). You can also give students the link directly.
When the class ends: `python admin.py close CLASS-A` unlocks the explanations for everyone.

## Editing questions

Edit `secret/questions.json`. `"stage"` is `warmup`, `main` (the default) or `advanced`: main questions are locked until all warm-up parts are solved, advanced ones until all main parts are solved.
Part types: `live`, `static` (regex `patterns`) and `mcq` (`options`, `answer` index). Live check kinds:

| Kind | Expects |
|---|---|
| `rrset` | records of `name`/`type` (options: `server`, `ecs`, `cd`, `all`, `match: prefix24`, `field`: keep one word of each record, e.g. 2 = SRV port) |
| `mx_primary`, `chain_len`, `auth_ttl` | best MX, number of names in the answer chain, TTL from an authoritative server |
| `rcode` | status (options: `server`, `cd`) |
| `txt_has`, `txt_count`, `txt_contains`, `txt_tag` | domains whose TXT holds a needle, how many of `list100.txt` do, `yes`/`no`, the value of a tag (`p` of DMARC) |
| `chaos_txt` | CH TXT answer of a `server` (`match: version` also accepts x.y.z alone) |
| `soa_field` | `mname`, `rname` (as an e-mail), `serial_date`, `serial`, `refresh`, `retry`, `expire`, `expire_days`, `minimum` |
| `ede_code` | Extended DNS Error code (retried: some anycast instances leave it out) |
| `null_mx` | which of `domains` publish `MX 0 .` |

`txt_count` reads `backend/data/list100.txt`; keep it in sync with `../list100.txt`.
Anycast answers (`hostname.bind`, NSID) depend on where you ask from, so grade them with a `static` pattern, not a live check.
