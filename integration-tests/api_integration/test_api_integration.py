"""
End-to-end integration test for the streamdaq API.

Starts the real API (``streamdaq serve``) as a subprocess, submits a two-task ``bulk_create``
payload (one sliding, one tumbling window) that exercises every instant check and every
measure over a finite, deterministic input stream, waits for the tasks to flush their
output files, then shuts the API down and asserts on the results.
"""

import os
import time
from pathlib import Path

import pytest
from utils import (
    RunningApi,
    get_running_streamdaq_api,
    http_post_json,
    verify_output_matches_expected,
    wait_until,
)

from api_integration.test_utils.payload import build_request_payload
from api_integration.test_utils.registry import EXCLUDED_MEASURES, MEASURE_SPECS
from streamdaq.api.registries import MEASURE_REGISTRY
from streamdaq.api.utils import API_PREFIX

EXPECTED_OUTPUT_DIR = Path(__file__).resolve().parent / "expected_output"
USER_FILES_DIR = Path(__file__).resolve().parent / "user_files"
SHOULD_UPDATE_EXPECTED_OUTPUT = os.getenv("STREAMDAQ_UPDATE_EXPECTED_OUTPUT") == "1"

OUTPUT_FILES_CREATION_TIMEOUT_SECONDS = 60.0


@pytest.fixture
def api_server(request, tmp_path):
    with get_running_streamdaq_api(tmp_path, request, files=str(USER_FILES_DIR)) as api:
        yield api


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
            verify_output_matches_expected(
                EXPECTED_OUTPUT_DIR, label, path, update=SHOULD_UPDATE_EXPECTED_OUTPUT
            )
