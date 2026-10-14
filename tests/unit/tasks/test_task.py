import json
import multiprocessing
from unittest.mock import MagicMock, patch

import dill
import pandas as pd
import pathway as pw

from streamdaq.checks.window.base import WindowDataQualityCheck
from streamdaq.measures.registry import MEASURE_REGISTRY
from streamdaq.orchestration.utils import load_additional_files
from streamdaq.tasks.base import Task, _run_task_in_worker

_MEASURE_NAME = "_SpawnSum"
_CHECK_NAME = "wc_spawn_sum"
_WORKER_JOIN_TIMEOUT_SECONDS = 30

_MEASURE_FILE = """
from streamdaq.custom import measure

@measure(["x"], name="_SpawnSum")
def _spawn_sum(d):
    return sum(d["x"])
"""


def _task() -> Task:
    return Task(input=lambda: None, output=lambda *a, **k: None, name="t")


def _build_input() -> pw.Table:
    frame = pd.DataFrame({"time": [1, 2, 3], "x": [1, 2, 3]})
    return pw.debug.table_from_pandas(frame)


def _resume_input() -> pw.Table:
    # event times span pre- and post-watermark windows
    frame = pd.DataFrame({"time": [100, 1100, 2100, 3100], "value": [1, 2, 3, 4]})
    return pw.debug.table_from_pandas(frame)


class TestResumeFromWatermark:
    """A resume watermark filters instant rows and shifts the window origin."""

    def test_instant_dag_filters_rows_at_or_after_watermark(self):
        from streamdaq.checks.instant.any_column.in_range import InRange

        task = Task(
            input=_resume_input,
            output=lambda *a, **k: None,
            windowby_column="time",
        )
        task.add_instant_checks(InRange(name="ic", column="value", low=0, high=1000))
        task._resume_instant_watermark = 2000

        instant_table = task._Task__construct_instant_pw_dag(_resume_input())
        times = sorted(pw.debug.table_to_pandas(instant_table)["time"].tolist())

        assert times == [2100, 3100]  # rows before the watermark are skipped

    def test_window_dag_uses_watermark_as_origin(self):
        from streamdaq.checks.window.base import WindowDataQualityCheck
        from streamdaq.measures.any_column.count import Count

        task = Task(
            input=_resume_input,
            output=lambda *a, **k: None,
            windowby_column="time",
            include_window_bounds=True,
        )
        task.add_window_checks(
            WindowDataQualityCheck("wc", Count(column="value"), ">= 1"),
            window=pw.temporal.tumbling(duration=1000),
        )
        task._resume_window_watermark = 2000

        window_table = task._Task__construct_window_pw_dag(_resume_input())
        starts = sorted(pw.debug.table_to_pandas(window_table)["window_start"].tolist())

        assert starts == [2000, 3000]  # no windows before the origin watermark

    def test_no_watermark_keeps_all_rows_and_windows(self):
        from streamdaq.checks.window.base import WindowDataQualityCheck
        from streamdaq.measures.any_column.count import Count

        task = Task(
            input=_resume_input,
            output=lambda *a, **k: None,
            windowby_column="time",
            include_window_bounds=True,
        )
        task.add_window_checks(
            WindowDataQualityCheck("wc", Count(column="value"), ">= 1"),
            window=pw.temporal.tumbling(duration=1000),
        )
        # resume watermarks default to None (fresh start)

        window_table = task._Task__construct_window_pw_dag(_resume_input())
        starts = sorted(pw.debug.table_to_pandas(window_table)["window_start"].tolist())

        assert starts == [0, 1000, 2000, 3000]  # every window is emitted


class TestTaskGracefullyKill:
    def test_no_op_when_process_never_started(self):
        task = _task()
        with patch("streamdaq.tasks.base.gracefully_kill") as mock_kill:
            task.gracefully_kill(timeout_seconds=5)
        mock_kill.assert_not_called()

    def test_delegates_to_orchestration_kill_when_process_exists(self):
        task = _task()
        task._pw_process = MagicMock()
        with patch("streamdaq.tasks.base.gracefully_kill") as mock_kill:
            task.gracefully_kill(timeout_seconds=5)
        mock_kill.assert_called_once_with(task._pw_process, 5)


class TestSpawnedWorker:
    def test_runs_real_task_in_spawned_worker(self, tmp_path):
        measure_file = tmp_path / "spawn_measure.py"
        measure_file.write_text(_MEASURE_FILE)
        output_file = tmp_path / "out.jsonl"
        window_output = tmp_path / "out_window.jsonl"

        load_additional_files(str(measure_file))
        check = WindowDataQualityCheck(_CHECK_NAME, MEASURE_REGISTRY[_MEASURE_NAME](), ">= 0")
        task = Task(
            input=_build_input,
            output=pw.io.jsonlines.write,
            output_kwargs={"filename": str(output_file)},
            windowby_column="time",
            files_path=str(measure_file),
        )
        task.add_window_checks(check, window=pw.temporal.tumbling(duration=10))

        payload = dill.dumps(task)
        ctx = multiprocessing.get_context("spawn")
        process = ctx.Process(target=_run_task_in_worker, args=(str(measure_file), payload))
        process.start()
        try:
            process.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)
        finally:
            if process.is_alive():
                process.terminate()
                process.join()

        assert process.exitcode == 0

        lines = [line for line in window_output.read_text().splitlines() if line.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])[_CHECK_NAME] is True
