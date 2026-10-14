"""End-to-end integration test for the task hot-swapping feature."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from utils import (
    RunningApi,
    get_running_streamdaq_api,
    http_post_json,
    verify_output_matches_expected,
    wait_until,
)

from streamdaq.api.utils import API_PREFIX
from task_hotswap_integration.test_utils.payload import (
    FINAL_INSTANT_OUTPUT,
    FINAL_WINDOW_OUTPUT,
    INITIAL_INSTANT_OUTPUT,
    INITIAL_WINDOW_OUTPUT,
    INPUT_FILENAME,
    TASK_NAME,
    build_initial_payload,
    build_updated_payload,
)
from task_hotswap_integration.test_utils.stream import (
    FIRST_BATCH,
    SECOND_BATCH,
    append_batch,
)

SUITE_DIR = Path(__file__).resolve().parent
EXPECTED_OUTPUT_DIR = SUITE_DIR / "expected_output"
SHOULD_UPDATE_EXPECTED_OUTPUT = os.getenv("STREAMDAQ_UPDATE_EXPECTED_OUTPUT") == "1"

INITIAL_FLUSH_TIMEOUT_SECONDS = 10.0
SWAP_LANDED_TIMEOUT_SECONDS = 3.0
OUTPUT_FILES_TIMEOUT_SECONDS = 60.0
UPDATED_INSTANT_HIGH = 25


@pytest.fixture
def api_server(request, tmp_path):
    with get_running_streamdaq_api(tmp_path, request) as api:
        yield api


def _served_instant_high(base_url: str) -> int | None:
    """Return the served task's instant-check ``high`` param, or None if not retrievable yet."""
    request = urllib.request.Request(f"{base_url}{API_PREFIX}/tasks/{TASK_NAME}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 200:
                return None
            config = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    instant_checks = config.get("instant_checks") or []
    if not instant_checks:
        return None
    return instant_checks[0].get("params", {}).get("high")


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def _expected_line_count(label: str) -> int:
    return _line_count(EXPECTED_OUTPUT_DIR / f"{label}.jsonl")


class TestTaskHotSwappingEndToEnd:
    def test_watermark_handover_splits_output_between_configs(self, api_server: RunningApi):
        work_dir = api_server.work_dir
        input_path = work_dir / INPUT_FILENAME
        input_path.touch()

        # Create the initial task reading from updates on a `.jsonl` file
        status, body = http_post_json(
            f"{api_server.base_url}{API_PREFIX}/bulk_create", build_initial_payload()
        )
        assert status == 201, f"initial bulk_create failed: {status} {body}"

        # Feed batch 1 to the initial task and wait until it produces its output
        append_batch(input_path, FIRST_BATCH)
        initial_outputs = [work_dir / INITIAL_INSTANT_OUTPUT, work_dir / INITIAL_WINDOW_OUTPUT]
        try:
            wait_until(
                lambda: all(path.exists() for path in initial_outputs),
                INITIAL_FLUSH_TIMEOUT_SECONDS,
                "the initial task to flush its output (and record its watermark)",
            )
        except TimeoutError as e:
            missing = [path.name for path in initial_outputs if not path.exists()]
            raise AssertionError(
                f"{e}. Initial task never produced: {missing}.\n"
                f"Server log:\n{api_server.server_log()}"
            ) from e

        # Hot-swap the same task (new thresholds + output file).
        status, body = http_post_json(
            f"{api_server.base_url}{API_PREFIX}/bulk_create", build_updated_payload()
        )
        assert status == 201, f"update bulk_create failed: {status} {body}"

        # Confirm the swap landed: the served config now reflects the updated threshold.
        try:
            wait_until(
                lambda: _served_instant_high(api_server.base_url) == UPDATED_INSTANT_HIGH,
                SWAP_LANDED_TIMEOUT_SECONDS,
                "the dynamic task update to be reflected in GET /tasks/{name}",
            )
        except TimeoutError as e:
            served = _served_instant_high(api_server.base_url)
            raise AssertionError(
                f"{e}. Served instant-check high={served!r}, expected {UPDATED_INSTANT_HIGH}. "
                f"The swap did not land within {SWAP_LANDED_TIMEOUT_SECONDS}s.\n"
                f"Server log:\n{api_server.server_log()}"
            ) from e

        # Feed batch 2; the swapped-in task resumes past the watermark and processes only it.
        append_batch(input_path, SECOND_BATCH)

        expected_files = {
            "output_initial_instant": work_dir / INITIAL_INSTANT_OUTPUT,
            "output_initial_window": work_dir / INITIAL_WINDOW_OUTPUT,
            "output_final_instant": work_dir / FINAL_INSTANT_OUTPUT,
            "output_final_window": work_dir / FINAL_WINDOW_OUTPUT,
        }

        # Wait until every file holds all its expected rows
        def _all_outputs_complete() -> bool:
            if SHOULD_UPDATE_EXPECTED_OUTPUT:
                return all(path.exists() for path in expected_files.values())
            return all(
                _line_count(path) >= _expected_line_count(label)
                for label, path in expected_files.items()
            )

        try:
            wait_until(
                _all_outputs_complete,
                OUTPUT_FILES_TIMEOUT_SECONDS,
                "all four output files to be fully written",
            )
        except TimeoutError as e:
            incomplete = [name for name, path in expected_files.items() if not path.exists()]
            raise AssertionError(
                f"{e}. Missing/incomplete outputs: {incomplete}.\n"
                f"Server log:\n{api_server.server_log()}"
            ) from e

        for label, path in expected_files.items():
            verify_output_matches_expected(
                EXPECTED_OUTPUT_DIR, label, path, update=SHOULD_UPDATE_EXPECTED_OUTPUT
            )
