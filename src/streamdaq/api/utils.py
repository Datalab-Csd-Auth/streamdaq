import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from streamdaq.api.routes import API_PREFIX


def is_API_running(host: str, port: int) -> bool:
    """Sends a quick HTTP probe to the health endpoint."""
    url = f"http://{host}:{port}{API_PREFIX}/heartbeat"
    try:
        req = Request(url, headers={"User-Agent": "streamdaq-cli"})
        with urlopen(req, timeout=1.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data.get("status").upper() == "OK"
    except (URLError, TimeoutError, ConnectionRefusedError, OSError):
        return False
    return False
