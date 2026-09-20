"""
End-to-end integration test for the feature of custom user code through decorators.

Starts the streamdaq API with user files (``streamdaq serve --files``) to verify
that custom user code is properly registered and remains usable through the API
as any other built-in measure. Verifies this by runnind a deterministic
finite stream and then comparing the output against the expected one.
"""

import os
from pathlib import Path

import pytest
from utils import (
    RunningApi,
    get_running_streamdaq_api,
    http_post_json,
    verify_output_matches_expected,
    wait_until,
)

from custom_integration.measures.payload import build_request_payload
from streamdaq.api.utils import API_PREFIX

EXPECTED_OUTPUT_DIR = Path(__file__).resolve().parent / "expected_output"
SHOULD_UPDATE = os.getenv("STREAMDAQ_UPDATE_EXPECTED_OUTPUT") == "1"
USER_FILES_DIR = str(Path(__file__).resolve().parent / "user_files")

OUTPUT_FILE_CREATION_TIMEOUT_SECONDS = 30.0
EXPECTED_WINDOW_ROWS = 2


@pytest.fixture
def api_server(request, tmp_path):
    with get_running_streamdaq_api(tmp_path, request, files=USER_FILES_DIR) as api:
        yield api


class TestCustomMeasureEndToEnd:
    def test_tumbling_window_custom_measure(self, api_server: RunningApi):
        work_dir = api_server.work_dir
        payload = build_request_payload("output.jsonl")

        status, body = http_post_json(f"{api_server.base_url}{API_PREFIX}/bulk_create", payload)
        assert status == 201, f"bulk_create failed: {status} {body}"

        output_path = work_dir / "output_window.jsonl"
        try:
            wait_until(
                lambda: output_path.exists(),
                OUTPUT_FILE_CREATION_TIMEOUT_SECONDS,
                "the output file to be populated by streamdaq API",
            )
        except TimeoutError as e:
            raise AssertionError(f"{e}. Server log:\n{api_server.server_log()}") from e

        verify_output_matches_expected(
            EXPECTED_OUTPUT_DIR, "tumbling_window", output_path, update=SHOULD_UPDATE
        )
