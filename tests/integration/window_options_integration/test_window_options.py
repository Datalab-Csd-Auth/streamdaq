"""End-to-end integration test for the Pathway-delegated window options."""

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
from window_options_integration.test_utils.payload import (
    INPUT_FILENAME,
    WINDOW_OUTPUT,
    WINDOW_OUTPUT_LABEL,
    build_payload,
)
from window_options_integration.test_utils.stream import (
    BATCHES_WITH_EXPECTED_WINDOW_ROWS,
    append_batch,
)

from streamdaq.api.utils import API_PREFIX

SUITE_DIR = Path(__file__).resolve().parent
EXPECTED_OUTPUT_DIR = SUITE_DIR / "expected_output"
SHOULD_UPDATE_EXPECTED_OUTPUT = os.getenv("STREAMDAQ_UPDATE_EXPECTED_OUTPUT") == "1"

SETTLE_SECONDS = 2.0
WINDOW_ROWS_TIMEOUT_SECONDS = 30.0


@pytest.fixture
def api_server(request, tmp_path):
    with get_running_streamdaq_api(tmp_path, request) as api:
        yield api


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text().splitlines() if line.strip())


class TestPathwayWindowOptionsEndToEnd:
    def test_late_arrivals_and_groups_shape_window_output(self, api_server: RunningApi):
        work_dir = api_server.work_dir
        input_path = work_dir / INPUT_FILENAME
        input_path.touch()
        window_output_path = work_dir / WINDOW_OUTPUT

        # Create the task reading from updates on a `.jsonl` file
        status, body = http_post_json(
            f"{api_server.base_url}{API_PREFIX}/bulk_create", build_payload()
        )
        assert status == 201, f"bulk_create failed: {status} {body}"

        for batch_index, (batch, expected_rows) in enumerate(BATCHES_WITH_EXPECTED_WINDOW_ROWS, 1):
            append_batch(input_path, batch)
            try:
                wait_until(
                    lambda expected=expected_rows: _line_count(window_output_path) >= expected,
                    WINDOW_ROWS_TIMEOUT_SECONDS,
                    f"batch {batch_index} to close windows ({expected_rows} window rows in total)",
                )
            except TimeoutError as e:
                raise AssertionError(
                    f"{e}. Window output holds {_line_count(window_output_path)} rows.\n"
                    f"Server log:\n{api_server.server_log()}"
                ) from e

        time.sleep(SETTLE_SECONDS)  # small buffer for pathway to flush the final window rows
        verify_output_matches_expected(
            EXPECTED_OUTPUT_DIR,
            WINDOW_OUTPUT_LABEL,
            window_output_path,
            update=SHOULD_UPDATE_EXPECTED_OUTPUT,
        )
