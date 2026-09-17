"""
End-to-end integration test for the streamdaq API.

Starts the real API (``run_api.py``) as a subprocess, submits a two-task ``bulk_create``
payload (one sliding, one tumbling window) that exercises every instant check and every
measure over a finite, deterministic input stream, waits for the tasks to flush their
output files, then shuts the API down and asserts on the results.
"""

import os
import re
import subprocess
import time
from collections import Counter
from pathlib import Path

import pytest
from utils import (
    INTEGRATION_TESTS_DIR,
    preserve_artifacts_if_failed,
    terminate_process_group,
    wait_until,
)

from api_integration.test_utils.api_communication import (
    RunningApi,
    find_a_free_port,
    http_post_json,
)
from api_integration.test_utils.payload import build_request_payload
from api_integration.test_utils.registry import EXCLUDED_MEASURES, MEASURE_SPECS
from streamdaq.api.registries import MEASURE_REGISTRY
from streamdaq.api.utils import API_PREFIX

EXPECTED_OUTPUT_DIR = Path(__file__).resolve().parent / "expected_output"
SHOULD_UPDATE_EXPECTED_OUTPUT = os.getenv("STREAMDAQ_UPDATE_EXPECTED_OUTPUT") == "1"

API_HOST = "127.0.0.1"
API_READINESS_TIMEOUT_SECONDS = 30.0
OUTPUT_FILES_CREATION_TIMEOUT_SECONDS = 60.0


def strip_system_time_from_lines(path: Path) -> list[str]:
    """Strip Pathway's non-deterministic processing-time field from all lines in the file"""
    system_time_matcher = r',"time":\d+}\s*$'
    replacement = "}"
    return [
        re.sub(system_time_matcher, replacement, line.strip())
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def compare_against_expected_output(label: str, output_path: Path) -> None:
    """Verify the output matches the expected one: same line count and same lines in any order"""
    expected_output_path = EXPECTED_OUTPUT_DIR / f"{label}.jsonl"
    output_lines = strip_system_time_from_lines(output_path)

    if SHOULD_UPDATE_EXPECTED_OUTPUT:
        EXPECTED_OUTPUT_DIR.mkdir(exist_ok=True)
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


@pytest.fixture
def api_server(request, tmp_path):
    port = find_a_free_port()
    base_url = f"http://{API_HOST}:{port}"

    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = os.pathsep.join(
        path for path in (INTEGRATION_TESTS_DIR, existing_pythonpath) if path
    )
    env = {**os.environ, "PYTHONPATH": pythonpath}
    log_path = tmp_path / "api.log"
    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            ["streamdaq", "serve", "--host", API_HOST, "--port", str(port)],
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
                        ["streamdaq", "status", "--host", API_HOST, "--port", str(port)],
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                    ).returncode
                    == 0
                ),
                API_READINESS_TIMEOUT_SECONDS,
                "streamdaq API to become ready and available",
            )
            yield RunningApi(base_url, tmp_path, log_path)
        finally:
            terminate_process_group(process)
            preserve_artifacts_if_failed(request, tmp_path)


class TestApiEndToEnd:
    def test_completeness_of_integration_tests(self):
        registered = set(MEASURE_REGISTRY)
        specified = set(MEASURE_SPECS)

        overlap = specified & EXCLUDED_MEASURES
        assert not overlap, f"Conflict: Measures both included and excluded: {sorted(overlap)}."

        accounted_for = specified | EXCLUDED_MEASURES
        unaccounted = registered - accounted_for
        assert not unaccounted, (
            f"Measures registered but not covered or excluded: {sorted(unaccounted)}. "
            "Add each to MEASURE_SPECS (with its params and must_be) or to EXCLUDED_MEASURES."
        )

        stale = accounted_for - registered
        assert not stale, f"Specs/exclusions reference unknown measures: {sorted(stale)}."

    def test_all_checks_and_measures(self, api_server: RunningApi):
        work_dir = api_server.work_dir
        payload = build_request_payload(
            sliding_output="sliding.jsonl", tumbling_output="tumbling.jsonl"
        )

        status, body = http_post_json(f"{api_server.base_url}{API_PREFIX}/bulk_create", payload)
        assert status == 201, f"bulk_create failed: {status} {body}"

        expected_files = {
            "sliding_instant": work_dir / "sliding.jsonl",
            "sliding_window": work_dir / "sliding_window.jsonl",
            "tumbling_instant": work_dir / "tumbling.jsonl",
            "tumbling_window": work_dir / "tumbling_window.jsonl",
        }

        try:
            wait_until(
                lambda: all(output_file.exists() for output_file in expected_files.values()),
                OUTPUT_FILES_CREATION_TIMEOUT_SECONDS,
                "all output files to be written",
            )
        except TimeoutError as e:
            missing = [
                file_name
                for file_name, file_path in expected_files.items()
                if not (file_path.exists() and file_path.stat().st_size)
            ]
            raise AssertionError(f"{e}. Missing outputs: {missing}.") from e

        time.sleep(2)  # Small time buffer for pathway to process all input
        for label, path in expected_files.items():
            compare_against_expected_output(label, path)
