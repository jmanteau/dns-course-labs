PY      := .venv/bin/python
CDK_PY  := infra/.venv/bin
COURSE  := ../../course
DECK    := $(COURSE)/_site/dns-advanced-single.html
CDK     := cd infra && PATH="$(CURDIR)/$(CDK_PY):$$PATH" npx aws-cdk
CODE    ?= CLASS-A
NAME    ?= $(CODE)
# the game server: BIND in Docker on an always-on host, reached over SSH
HOST    ?= oraclevm
REMOTE  ?= dig-quest-server
SRV_DIR := build/server
# local simulation: the game zone, the game server and a resolver in containers (podman: docker-compose on PATH)
COMPOSE ?= $(shell command -v docker >/dev/null && echo docker compose || echo podman compose)
SIM_DIR := build/sim
SIM     := $(COMPOSE) -f $(SIM_DIR)/compose.yaml

.PHONY: help setup dev test live zone-check server-check deck synth deploy deploy-zone \
        server-build server-deploy server-logs server-firewall \
        sim-build sim-up sim-test sim-dev sim-down session close reopen clean

.DEFAULT_GOAL := help

help:
	@echo "make setup        create .venv (game, tests) and infra/.venv (CDK)"
	@echo "make dev          play locally: http://localhost:8787/?session=DEV (board, /_debug viewer)"
	@echo "make test         unit tests (mocked DNS and DynamoDB)"
	@echo "make live         before a class: every live question still answerable, game zone and server as specified"
	@echo "make zone-check   after a deploy or a zone.json edit: the game zone matches the spec"
	@echo "make deck         build the advanced slides the game links to ($(DECK))"
	@echo "make synth        CDK synth of both stacks (needs AWS credentials: jmanteau.fr lookup)"
	@echo "make deploy       build the deck, then deploy the game and the game zone (not during a class)"
	@echo "make deploy-zone  deploy only the game zone (DigQuestZone, with the game server's records)"
	@echo "make server-build   render the game server's Docker folder from secret/server.json ($(SRV_DIR))"
	@echo "make server-deploy  copy it to $(HOST):~/$(REMOTE) and (re)start BIND there (HOST=... to change)"
	@echo "make server-logs    last lines of both BIND containers on $(HOST)"
	@echo "make server-firewall  once: open 53 and 8053 (UDP, TCP) in the host firewall of $(HOST) (sudo)"
	@echo "make server-check   the game server serves what secret/server.json describes"
	@echo "make sim-test     local simulation: game zone + game server + resolver in containers, then every test"
	@echo "                  (unit, live, sim) against it: waves 2 and 3 work before anything is deployed"
	@echo "make sim-dev      play on http://localhost:8787/?session=DEV against the local simulation"
	@echo "make sim-up       start only the simulated DNS (sim-build renders it in $(SIM_DIR))"
	@echo "make sim-down     stop and remove the simulation"
	@echo "make session CODE=CLASS-A NAME=\"IUT Blagnac A\"   create a class session"
	@echo "make close CODE=CLASS-A    close it: unlocks every explanation"
	@echo "make reopen CODE=CLASS-A   reopen it"
	@echo "make clean        remove build output (build/, caches)"
	@echo "session commands need QUEST_API and QUEST_ADMIN_SECRET_ARN (or QUEST_ADMIN_TOKEN): see README.md"

setup:
	python3 -m venv .venv && $(PY) -m pip install -q dnspython "moto[server]" pytest boto3
	python3 -m venv infra/.venv && $(CDK_PY)/pip install -q -r infra/requirements.txt

dev: $(DECK)
	$(PY) dev_server.py

test:
	$(PY) -m pytest

live:
	$(PY) -m pytest -m live

zone-check:
	$(PY) -m pytest -m live -k "game_zone or wildcard"

server-check:
	$(PY) -m pytest -m live -k game_server

deck: $(DECK)

# the game serves this file as deck/dns-advanced.html: rebuilt when the slides change
$(DECK): $(COURSE)/dns-advanced.qmd $(COURSE)/theme/dns.scss
	$(MAKE) -C $(COURSE) single DECK=dns-advanced

synth:
	$(CDK) synth --all

deploy: $(DECK)
	$(CDK) deploy --all

deploy-zone:
	$(CDK) deploy DigQuestZone

server-build:
	$(PY) infra/game_server.py secret/server.json $(SRV_DIR)

server-deploy: server-build
	ssh $(HOST) "rm -rf $(REMOTE)/quest && mkdir -p $(REMOTE)"
	tar -C $(SRV_DIR) -cf - . | ssh $(HOST) "tar -C $(REMOTE) -xf -"
	ssh $(HOST) "cd $(REMOTE) && docker compose up -d --build && docker compose ps"

server-logs:
	ssh $(HOST) "cd $(REMOTE) && docker compose logs --tail 30"

# Oracle images block everything but SSH: iptables (Ubuntu) or firewalld (Oracle Linux).
# The VCN security list must allow the same ports: add those ingress rules in the Oracle console.
server-firewall:
	ssh -t $(HOST) 'set -e; for p in 53 8053; do for t in udp tcp; do \
	  if command -v firewall-cmd >/dev/null; then sudo firewall-cmd -q --permanent --add-port=$$p/$$t; \
	  else sudo iptables -C INPUT -p $$t --dport $$p -j ACCEPT 2>/dev/null || sudo iptables -I INPUT -p $$t --dport $$p -j ACCEPT; fi; \
	done; done; \
	if command -v firewall-cmd >/dev/null; then sudo firewall-cmd -q --reload; else sudo netfilter-persistent save; fi; echo opened'

sim-build:
	$(PY) infra/sim.py secret $(SIM_DIR)

# always from scratch: podman cannot recreate main while alt shares its network
sim-up: sim-build
	$(SIM) --profile runner down --remove-orphans 2>/dev/null || true
	$(SIM) up -d --build resolver zone main alt
	$(SIM) build runner

sim-test: sim-up
	$(SIM) run --rm --no-deps runner sh -c 'env -u QUEST_RESOLVER -u DIG_ALLOW_NET -u GAME_SERVER pytest -p no:cacheprovider -q \
	  && pytest -p no:cacheprovider -m "live or sim"' 

sim-dev: sim-up
	$(SIM) run --rm --no-deps --service-ports runner python dev_server.py

sim-down:
	$(SIM) --profile runner down --remove-orphans

session:
	$(PY) admin.py create $(CODE) "$(NAME)"

close:
	$(PY) admin.py close $(CODE)

reopen:
	$(PY) admin.py reopen $(CODE)

clean:
	rm -rf build .pytest_cache infra/cdk.out
