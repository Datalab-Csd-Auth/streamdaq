import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from pytest import FixtureRequest

ARTIFACTS_DIR = Path(__file__).resolve().parent / ".artifacts"
INTEGRATION_TESTS_DIR = str(Path(__file__).resolve().parent)


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
