import docker
from docker.errors import NotFound


ALLOWED_CONTAINERS = frozenset({
    "client", "dns_internal", "dns_public",
    "c2_server", "webserver", "firewall",
})


class DockerManager:
    def __init__(self):
        self.client = docker.from_env()

    def get_container(self, name: str):
        if name not in ALLOWED_CONTAINERS:
            raise ValueError(f"Container '{name}' is not part of the lab")
        return self.client.containers.get(name)

    def list_containers(self) -> list:
        results = []
        for name in sorted(ALLOWED_CONTAINERS):
            try:
                c = self.client.containers.get(name)
                networks = {}
                for net_name, net_info in c.attrs["NetworkSettings"]["Networks"].items():
                    networks[net_name] = net_info.get("IPAddress", "")
                results.append({
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown",
                    "networks": networks,
                })
            except NotFound:
                results.append({"name": name, "status": "not_found", "networks": {}})
            except Exception:
                results.append({"name": name, "status": "error", "networks": {}})
        return results

    def exec_command(self, container_name: str, command: str) -> dict:
        container = self.get_container(container_name)
        exit_code, output = container.exec_run(
            cmd=["/bin/sh", "-c", command],
            demux=True,
            tty=False,
        )
        return {
            "exit_code": exit_code,
            "stdout": output[0].decode(errors="replace") if output[0] else "",
            "stderr": output[1].decode(errors="replace") if output[1] else "",
        }

    def create_terminal(self, container_name: str):
        """Create an interactive PTY exec session. Returns (exec_id, socket)."""
        container = self.get_container(container_name)
        exec_id = self.client.api.exec_create(
            container.id,
            "/bin/sh",
            stdin=True,
            tty=True,
            stdout=True,
            stderr=True,
        )
        sock = self.client.api.exec_start(exec_id, socket=True, tty=True)
        return exec_id, sock

    def resize_terminal(self, exec_id: dict, rows: int, cols: int):
        try:
            self.client.api.exec_resize(exec_id, height=rows, width=cols)
        except Exception:
            pass
