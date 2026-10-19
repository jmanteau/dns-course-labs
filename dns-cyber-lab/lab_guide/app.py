import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from analysis_engine import AnalysisEngine
from docker_manager import DockerManager, ALLOWED_CONTAINERS
from lab_steps import LAB_STEPS

BASE_DIR = Path(__file__).parent
DNS_LOG_DIR = os.environ.get("DNS_LOG_DIR", str(BASE_DIR.parent / "dns_internal" / "var" / "log"))

dm: DockerManager
analysis: AnalysisEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    global dm, analysis
    dm = DockerManager()
    analysis = AnalysisEngine(DNS_LOG_DIR)
    yield


app = FastAPI(title="DNS Cyber Lab Guide", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/containers")
async def list_containers():
    return await asyncio.to_thread(dm.list_containers)


class ExecRequest(BaseModel):
    command: str


@app.post("/api/containers/{name}/exec")
async def exec_command(name: str, req: ExecRequest):
    if name not in ALLOWED_CONTAINERS:
        return {"error": f"Container '{name}' not in lab"}
    return await asyncio.to_thread(dm.exec_command, name, req.command)


@app.get("/api/lab/steps")
async def get_steps():
    return LAB_STEPS


@app.get("/api/analysis/run")
async def run_analysis():
    # First try to convert logs via docker exec
    try:
        await asyncio.to_thread(
            dm.exec_command,
            "dns_internal",
            "dnstap-read -y /var/log/log.dnstap > /var/log/dnslog.txt",
        )
    except Exception:
        pass
    ok = await asyncio.to_thread(analysis.parse_logs, True)
    if not ok:
        return {"error": "No DNS logs found. Run the lab first and convert logs."}
    thresholds = DEFAULT_THRESHOLDS.copy()
    weights = DEFAULT_WEIGHTS.copy()
    return await asyncio.to_thread(analysis.score_all, thresholds, weights, 4.5)


class ScoreRequest(BaseModel):
    thresholds: dict
    weights: dict
    threshold_score: float = 4.5


@app.post("/api/analysis/score")
async def rescore(req: ScoreRequest):
    if not analysis._fqdn_metrics:
        return {"error": "No data parsed yet. Run analysis first."}
    return await asyncio.to_thread(
        analysis.score_all, req.thresholds, req.weights, req.threshold_score
    )


@app.get("/api/rpz")
async def get_rpz():
    try:
        result = await asyncio.to_thread(
            dm.exec_command, "dns_internal", "cat /etc/bind/rpz.zone"
        )
        return {"content": result["stdout"]}
    except Exception as e:
        return {"error": str(e)}


class RpzEntry(BaseModel):
    domain: str


@app.post("/api/rpz")
async def add_rpz(entry: RpzEntry):
    domain = entry.domain.strip().rstrip(".")
    lines = [
        f"{domain}.rpz.       CNAME   *.",
        f"*.{domain}.rpz.     CNAME   *.",
    ]
    cmd = " && ".join(
        [f"echo '{line}' >> /etc/bind/rpz.zone" for line in lines]
        + ["named-checkzone rpz /etc/bind/rpz.zone", "rndc reload"]
    )
    result = await asyncio.to_thread(dm.exec_command, "dns_internal", cmd)
    return result


@app.websocket("/ws/terminal/{container_name}")
async def ws_terminal(websocket: WebSocket, container_name: str):
    await websocket.accept()
    if container_name not in ALLOWED_CONTAINERS:
        await websocket.close(code=4000, reason="Invalid container")
        return

    try:
        exec_id, sock = await asyncio.to_thread(dm.create_terminal, container_name)
    except Exception as e:
        await websocket.send_text(f"\r\nError: {e}\r\n")
        await websocket.close()
        return

    # Get the raw socket from Docker SDK's wrapper
    raw_sock = sock._sock if hasattr(sock, '_sock') else sock
    loop = asyncio.get_event_loop()
    closed = asyncio.Event()

    async def read_docker():
        """Read from Docker PTY socket, send to browser."""
        try:
            while not closed.is_set():
                try:
                    data = await asyncio.wait_for(
                        loop.run_in_executor(None, _read_sock, raw_sock),
                        timeout=1.0,
                    )
                    if data:
                        await websocket.send_bytes(data)
                    elif data == b"":
                        break
                except asyncio.TimeoutError:
                    continue
                except (ConnectionError, OSError):
                    break
        except Exception:
            pass
        finally:
            closed.set()

    async def read_browser():
        """Read from browser WebSocket, write to Docker PTY socket."""
        try:
            while not closed.is_set():
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                data = msg.get("bytes") or (msg.get("text", "").encode())
                if not data:
                    continue
                if data.startswith(b'{"type":"resize"'):
                    try:
                        resize = json.loads(data)
                        await asyncio.to_thread(
                            dm.resize_terminal, exec_id, resize["rows"], resize["cols"]
                        )
                        continue
                    except (json.JSONDecodeError, KeyError):
                        pass
                try:
                    await loop.run_in_executor(None, raw_sock.sendall, data)
                except (BrokenPipeError, OSError):
                    break
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            closed.set()

    try:
        await asyncio.gather(read_docker(), read_browser())
    finally:
        try:
            raw_sock.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


def _read_sock(sock) -> bytes:
    """Blocking read from socket with short timeout."""
    import select
    try:
        sock.setblocking(False)
    except OSError:
        pass
    ready, _, _ = select.select([sock], [], [], 0.3)
    if ready:
        try:
            data = sock.recv(4096)
            return data if data else b""
        except (BlockingIOError, ConnectionError, OSError):
            return b""
    return None


DEFAULT_THRESHOLDS = {
    "entropy": {"value": 4.0, "direction": "greater"},
    "non_letter_ratio": {"value": 0.3, "direction": "greater"},
    "hex_char_ratio": {"value": 0.5, "direction": "greater"},
    "vowel_ratio": {"value": 0.3, "direction": "less"},
    "n_gram_2": {"value": 10.0, "direction": "less"},
    "gini_index": {"value": 0.9, "direction": "greater"},
    "classification_error": {"value": 0.85, "direction": "greater"},
    "number_of_labels": {"value": 3, "direction": "greater"},
    "average_interval": {"value": 5.0, "direction": "less"},
    "payload_size": {"value": 50, "direction": "greater"},
}

DEFAULT_WEIGHTS = {
    "entropy": 1.5,
    "non_letter_ratio": 0.8,
    "hex_char_ratio": 0.8,
    "vowel_ratio": 1.0,
    "n_gram_2": 0.9,
    "gini_index": 1.0,
    "classification_error": 0.5,
    "number_of_labels": 1.1,
    "average_interval": 1.1,
    "payload_size": 2.0,
}
