import json
import os
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from pytest import FixtureRequest

ARTIFACTS_DIR = Path(__file__).resolve().parent / ".artifacts"
INTEGRATION_TESTS_DIR = str(Path(__file__).resolve().parent)

API_HOST = "127.0.0.1"
API_READINESS_TIMEOUT_SECONDS = 30.0


def preserve_artifacts_if_failed(request: FixtureRequest, work_dir: Path) -> None:
    failed = any(
        getattr(request.node, f"report_{phase}", None) is not None
        and getattr(request.node, f"report_{phase}").failed
        for phase in ("setup", "call")
    )
    if not failed:
        return

    destination = ARTIFACTS_DIR / request.node.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(work_dir, destination)
    print(f"\nIntegration tests failed! Debug artifacts are saved to '{destination}'.")


def terminate_process_group(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    group = os.getpgid(process.pid)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(group, sig)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=15)
            return
        except subprocess.TimeoutExpired:
            continue


def wait_until(predicate, timeout_s: float, description: str, poll_interval_seconds: int = 0.25):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(poll_interval_seconds)
    raise TimeoutError(f"Timed out after {timeout_s}s waiting for: {description}")


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


def strip_system_time_from_lines(path: Path) -> list[str]:
    """Strip Pathway's non-deterministic processing-time field from all lines in the file"""
    system_time_matcher = r',"time":\d+}\s*$'
    replacement = "}"
    return [
        re.sub(system_time_matcher, replacement, line.strip())
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def verify_output_matches_expected(
    expected_output_dir: Path, label: str, output_path: Path, *, update: bool
) -> None:
    """Verify the output matches the expected one: same line count and same lines in any order"""
    expected_output_path = expected_output_dir / f"{label}.jsonl"
    output_lines = strip_system_time_from_lines(output_path)

    if update:
        expected_output_dir.mkdir(exist_ok=True)
        expected_output_path.write_text("\n".join(sorted(output_lines)) + "\n")
        return

    assert expected_output_path.exists(), (
        f"Missing expected_output file for '{label}': {expected_output_path}. "
        "Generate expected outputs with STREAMDAQ_UPDATE_EXPECTED_OUTPUT=1."
    )
    expected_output_lines = [
        line for line in expected_output_path.read_text().splitlines() if line.strip()
    ]

    assert len(output_lines) == len(expected_output_lines), (
        f"{label}: expected {len(expected_output_lines)} output lines, got {len(output_lines)}."
    )
    assert Counter(output_lines) == Counter(expected_output_lines), (
        f"{label}: output lines do not match the expected_output file (order-insensitive).\n"
        f"Only in output: {sorted(Counter(output_lines) - Counter(expected_output_lines))}\n"
        f"Only in expected_output: {sorted(Counter(expected_output_lines) - Counter(output_lines))}"
    )


@contextmanager
def get_running_streamdaq_api(
    tmp_path: Path,
    request: FixtureRequest,
    *,
    files: str | None = None,
    host: str = API_HOST,
    readiness_timeout_s: float = API_READINESS_TIMEOUT_SECONDS,
) -> Generator[RunningApi]:
    port = find_a_free_port()
    base_url = f"http://{host}:{port}"

    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = os.pathsep.join(
        path for path in (INTEGRATION_TESTS_DIR, existing_pythonpath) if path
    )
    env = {**os.environ, "PYTHONPATH": pythonpath}
    log_path = tmp_path / "api.log"

    serve_command = ["streamdaq", "serve", "--host", host, "--port", str(port)]
    if files:
        serve_command += ["--files", files]

    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            serve_command,
            cwd=tmp_path,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        try:
            wait_until(
                lambda: (
                    subprocess.run(
                        ["streamdaq", "status", "--host", host, "--port", str(port)],
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                    ).returncode
                    == 0
                ),
                readiness_timeout_s,
                "streamdaq API to become ready and available",
            )
            yield RunningApi(base_url, tmp_path, log_path)
        finally:
            terminate_process_group(process)
            preserve_artifacts_if_failed(request, tmp_path)
