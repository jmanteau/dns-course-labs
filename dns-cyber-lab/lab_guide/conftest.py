"""
Integration test fixtures for DNS Cyber Lab.

Requires: lab running (`make up` from dns-cyber-lab/).
Run with: uv run pytest -v
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from docker_manager import DockerManager, ALLOWED_CONTAINERS


def _docker_available():
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


def _container_cli():
    """Return 'podman' or 'docker', whichever is on PATH."""
    for cli in ("podman", "docker"):
        if shutil.which(cli):
            return cli
    return "docker"


@pytest.fixture(scope="session")
def dm():
    if not _docker_available():
        pytest.skip("Docker not available or not running")
    return DockerManager()


@pytest.fixture(scope="session")
def lab_running(dm):
    """Skip the whole session if any required container is not running."""
    for name in ALLOWED_CONTAINERS:
        try:
            c = dm.client.containers.get(name)
            if c.status != "running":
                pytest.skip(f"Container '{name}' is {c.status}. Run `make up` first.")
        except Exception:
            pytest.skip(f"Container '{name}' not found. Run `make up` first.")


@pytest.fixture(scope="session")
def run(dm, lab_running):
    """run(container, cmd) -> {exit_code, stdout, stderr}"""

    def _run(container: str, command: str):
        return dm.exec_command(container, command)

    return _run


@pytest.fixture(scope="session")
def run_cli(lab_running):
    """run_cli(container, cmd, timeout) -> {exit_code, stdout, stderr}

    Uses podman/docker CLI via subprocess — avoids Docker SDK socket hang
    on Podman for long-running commands with demux=True.
    """
    cli = _container_cli()

    def _run(container: str, command: str, timeout: int = 120):
        if container not in ALLOWED_CONTAINERS:
            raise ValueError(f"Container '{container}' is not part of the lab")
        r = subprocess.run(
            [cli, "exec", container, "/bin/sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": r.returncode,
            "stdout": r.stdout,
            "stderr": r.stderr,
        }

    return _run
