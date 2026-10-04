"""
End-to-end integration tests for custom user code loaded through ``streamdaq serve --files``.

A custom ``@measure``, ``@assessment``, ``@source`` and ``@sink`` are registered from the shared
``user_files`` and driven over the API against the same deterministic finite stream.
Each task's output is compared against its expected output.
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

from custom_integration.assessments.payload import build_request_payload as build_assessment_payload
from custom_integration.measures.payload import build_request_payload as build_measure_payload
from custom_integration.sinks.payload import build_request_payload as build_sink_payload
from custom_integration.sources.payload_compact import build_compact_request_payload
from custom_integration.sources.payload_native import build_native_request_payload
from streamdaq.api.utils import API_PREFIX

SUITE_DIR = Path(__file__).resolve().parent
SHOULD_UPDATE = os.getenv("STREAMDAQ_UPDATE_EXPECTED_OUTPUT") == "1"
USER_FILES_DIR = str(SUITE_DIR / "user_files")

OUTPUT_ROWS_TIMEOUT_SECONDS = 60.0
EXPECTED_WINDOW_ROWS = 2


def count_nonempty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text().splitlines() if line.strip())


@pytest.fixture
def api_server(request, tmp_path):
    with get_running_streamdaq_api(tmp_path, request, files=USER_FILES_DIR) as api:
        yield api


class TestCustomUserCodeEndToEnd:
    @pytest.mark.parametrize(
        "build_payload, expected_output_dir",
        [
            (build_measure_payload, SUITE_DIR / "measures" / "expected_output"),
            (build_assessment_payload, SUITE_DIR / "assessments" / "expected_output"),
            (build_native_request_payload, SUITE_DIR / "sources" / "expected_output_native"),
            (build_compact_request_payload, SUITE_DIR / "sources" / "expected_output_compact"),
            (build_sink_payload, SUITE_DIR / "sinks" / "expected_output"),
        ],
        ids=[
            "custom_measure",
            "custom_assessment",
            "custom_source",
            "custom_compact_source",
            "custom_sink",
        ],
    )
    def test_tumbling_window(self, api_server: RunningApi, build_payload, expected_output_dir):
        work_dir = api_server.work_dir
        payload = build_payload("output.jsonl")

        status, body = http_post_json(f"{api_server.base_url}{API_PREFIX}/bulk_create", payload)
        assert status == 201, f"bulk_create failed: {status} {body}"

        output_path = work_dir / "output_window.jsonl"
        try:
            wait_until(
                lambda: count_nonempty_lines(output_path) >= EXPECTED_WINDOW_ROWS,
                OUTPUT_ROWS_TIMEOUT_SECONDS,
                f"the window output to reach {EXPECTED_WINDOW_ROWS} rows",
            )
        except TimeoutError as e:
            raise AssertionError(f"{e}. Server log:\n{api_server.server_log()}") from e

        verify_output_matches_expected(
            expected_output_dir, "tumbling_window", output_path, update=SHOULD_UPDATE
        )
