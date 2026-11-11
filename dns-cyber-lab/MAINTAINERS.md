# DNS security lab: maintainer notes

How the cyber lab is built, which versions it uses, how to test it and how to fix common problems. For teachers and maintainers. Updated November 2026.

Students: follow the [lab guide](README.md) instead.

## Contents

- [What runs where](#what-runs-where)
- [Commands](#commands)
- [Test the lab end to end](#test-the-lab-end-to-end)
- [Sliver version](#sliver-version)
- [Fix common problems](#fix-common-problems)
- [Supported hosts](#supported-hosts)
- [Design history](#design-history)

## What runs where

| Path | What it holds |
|------|---------------|
| `docker-compose.yml` | The lab's containers and networks. Uses Docker Compose v2 syntax (`docker compose`, with a space) |
| `dns_base/Dockerfile` | The BIND 9 image shared by both DNS servers: Alpine 3.20, multi-arch (amd64 and arm64) |
| `dns_public/`, `dns_internal/` | Configuration, zones and `start.sh` of the public and internal DNS servers. `start.sh` fixes the permissions of the mounted folders for the `named` user, then starts BIND |
| `dns_internal/analysis.py` | The detection script students run in the blue team part |
| `c2_server/Dockerfile` | Debian slim image that downloads the Sliver server and client for the host's architecture. Version in `SLIVER_RELEASE` |
| `c2_server/entrypoint.sh` | Initialises the Sliver server: unpacks its assets and generates the operator configuration |
| `lab_guide/` | The step-by-step web guide (FastAPI) on http://localhost:8085, with the end-to-end tests (`test_lab.py`) |
| `toplist/`, `shared-data/` | The top 10,000 domains used to generate normal traffic, and the folder shared between containers (the implant is saved there) |
| `Makefile` | Shortcuts for every command. It uses Podman when installed, otherwise Docker |

## Commands

Run `make help` for the full list.

**Install** (Amazon Linux 2023 only, once per system):

- `make install` installs git, Docker (Moby), the Docker Compose v2 plugin and Docker Buildx, then clones or refreshes the repository. Log out and back in afterwards (or run `newgrp docker`) so the docker group change applies.

**Run the containers:**

| Command | What it does |
|---------|--------------|
| `make build` | Build all images without starting the containers |
| `make up` | Start all containers, building the images if needed |
| `make stop` | Stop all containers without removing them |
| `make restart` | Restart all containers |
| `make destroy` | Remove the containers, images, volumes and build cache |
| `make ps` | Status of all containers, stopped ones included |
| `make ls` | Running containers, as a table |
| `make info` | Status, IP addresses, ports and networks of every container |
| `make validate` | Check that the client resolves names and the C2 zone |
| `make logs1`, `make logs5` | Logs of the last 1 or 5 minutes |

**Open a shell in a container:** `make <container>_shell`, for the containers `c2_server` (Sliver), `client`, `dns_internal`, `dns_public`, `firewall` and `webserver`. For example `make client_shell`.

## Test the lab end to end

`lab_guide/test_lab.py` follows the lab guide's steps: environment checks, the red team steps, the blue team steps (log analysis, tuning, RPZ blocking) and the bonus DNS infiltration step. Start the lab first, then:

```bash
cd dns-cyber-lab/lab_guide
uv run pytest test_lab.py -v
```

## Sliver version

The C2 server image downloads **Sliver v1.7.8**. To change it:

1. Edit `ENV SLIVER_RELEASE` in `c2_server/Dockerfile`.
2. Rebuild: `make destroy && make build && make up`.
3. Run the end-to-end tests: the DNS transport is the part that breaks between Sliver releases.

Avoid Sliver 1.5.39 to 1.5.44. In those versions, the DNS listener could fail to start, and sessions connected then died at once.

## Fix common problems

### DNS containers stop with "permission denied"

**What you see:** `dns_public` or `dns_internal` exits at once, with an error such as "directory '/var/cache/bind' is not writable" or "/etc/bind/named.conf: parsing failed: permission denied".

**Why:** BIND runs as the `named` user and needs write access to the mounted folders.

**Fix:** `start.sh` fixes the permissions each time the container starts. The DNS containers run with `privileged: true` and `cap_add: NET_ADMIN`, which they need for that. If the problem stays:

```bash
make restart
docker compose logs dns_public
docker compose logs dns_internal
```

### Every Sliver session is [DEAD]

**What you see:** `sessions` in Sliver shows only `[DEAD]` sessions.

**Why:** C2 over DNS is fragile by nature: it runs over UDP, and sessions time out or drop.

**Fix:** this is expected. Tell students to:

1. Restart the implant on the client (`Ctrl+C`, then run it again).
2. Wait 5 to 10 seconds for it to reconnect.
3. Run `sessions` again and look for `[ALIVE]` sessions.
4. Use only alive sessions.
5. If drops keep happening, generate the implant with a longer reconnect interval: `--reconnect 5`.

### The build fails with "failed to copy xattrs"

**What you see:** on macOS, with Podman or some Docker setups:

```
failed to copy xattrs: failed to set xattr "security.selinux" on ...: operation not supported
```

**Why:** BuildKit tries to keep the SELinux extended attributes (xattrs) of copied files. macOS file systems do not support these Linux attributes.

**Fix:** build with the legacy builder: run the build with `DOCKER_BUILDKIT=0` set.

### "compose build requires buildx 0.17 or later"

**Why:** docker-compose is outdated, or the buildx plugin is missing.

**Fix:** on Amazon Linux 2023, run `make install`. It installs the Docker Compose v2 plugin (not the standalone v1) and Docker Buildx 0.17.1 or later.

### Containers crash on an ARM Mac with an amd64 image

**What you see:** a container exits with code 139, or crashes.

**Why:** running x86 programs on ARM needs QEMU emulation to be set up.

**Fix:** the lab's own images are multi-arch, so this concerns only an image pulled for amd64. Register the emulators, then start again:

```bash
docker run --rm --privileged tonistiigi/binfmt --install all
make up
```

## Supported hosts

Students can run the lab on:

- x86 Linux;
- Windows with Docker Desktop;
- Amazon Linux 2023 EC2 instances;
- macOS, with Docker or Podman (the images are multi-arch).

To prepare an Amazon Linux 2023 host:

```bash
git clone https://github.com/jmanteau/dns-course-labs.git
cd dns-course-labs/dns-cyber-lab
make install
```

## Design history

Earlier versions of the lab forced every container to `linux/amd64`, because Sliver 1.5.34 to 1.5.44 depended on gvisor, whose low-level code was x86 only. They also disabled BuildKit in the Makefile (`DOCKER_BUILDKIT=0`). The current images are multi-arch and the Makefile no longer sets BuildKit, so neither constraint applies today.
