import json
import socket
import urllib.error
import urllib.request
from pathlib import Path


def find_a_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def http_post_json(url: str, body: list) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


class RunningApi:
    def __init__(self, base_url: str, work_dir: Path, log_path: Path):
        self.base_url = base_url
        self.work_dir = work_dir
        self.log_path = log_path

    def server_log(self) -> str:
        return self.log_path.read_text() if self.log_path.exists() else ""
