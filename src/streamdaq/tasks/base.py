import dataclasses
import multiprocessing
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

import dill
import pathway as pw

from streamdaq.checks.base import DataQualityCheck
from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.checks.window.base import WindowDataQualityCheck
from streamdaq.io.sources import BaseSource
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.orchestration.utils import gracefully_kill, load_additional_files
from streamdaq.storage.watermark_store import WatermarkStore
from streamdaq.tasks.task_output import TaskOutput
from streamdaq.temporal.windows.commons import WINDOW_END_COLUMN_NAME, WINDOW_START_COLUMN_NAME
from streamdaq.windows.base import Window


def _run_task_in_worker(files_path: str | None, task_payload: bytes) -> None:
    # Reload user files before deserializing the task for MacOS multiprocessing compatibility
    if files_path:
        load_additional_files(files_path)

    task = dill.loads(task_payload)
    if isinstance(task.input, BaseSource):
        task.input.files_path = files_path
    task._pw_task_worker_function()


@dataclass
class Task:
    input: Callable[[Any], pw.Table]
    output: Callable[[Any], None] | TaskOutput
    name: str | None = None
    instant_checks: list[InstantDataQualityCheck] = field(default_factory=lambda: [])
    window_checks: list[WindowDataQualityCheck] = field(default_factory=lambda: [])
    window: Window | None = None
    windowby_column: str | None = None
    wait_for_late: int | None = None
    include_window_bounds: bool = True
    include_streamdaq_metadata: bool = True
    input_kwargs: dict[str, Any] = field(default_factory=lambda: {})
    output_kwargs: dict[str, Any] = field(default_factory=lambda: {})
    files_path: str | None = None
    watermark_path: str | None = None
    version: int = 1

    def __post_init__(self):
        self.instant_table: pw.Table | None = None
        self.window_table: pw.Table | None = None
        self._pw_process: multiprocessing.Process | None = None
        self._resume_instant_watermark: int | None = None
        self._resume_window_watermark: int | None = None

    def add_instant_checks(self, *instant_checks: InstantDataQualityCheck) -> Self:
        for instant_check in instant_checks:
            self.instant_checks.append(instant_check)
        return self

    def add_window_checks(self, *window_checks: WindowDataQualityCheck, window: Window) -> Self:
        self.window = window
        for window_check in window_checks:
            self.window_checks.append(window_check)
        return self

    def add_checks(self, *checks: DataQualityCheck, window: Window | None = None) -> Self:
        instant_checks = [check for check in checks if isinstance(check, InstantDataQualityCheck)]
        window_checks = [check for check in checks if isinstance(check, WindowDataQualityCheck)]
        if len(window_checks) > 0 and window is None:
            raise ValueError("TODO CANNOT INSTANTIATE WINDOW CHECKS WITHOUT WINDOW")

        if len(window_checks) == 0 and window is not None:
            raise ValueError(
                "TODO WINDOW IS PROVIDED BUT NO WINDOW CHECKS",
                "WINDOW WILL BE IGNORED BUT PROBABLY THIS IS NOT WHAT YOU WANT",
            )

        self.add_instant_checks(*instant_checks)
        self.add_window_checks(*window_checks)

        return self

    def gracefully_kill(self, timeout_seconds: int) -> None:
        if self._pw_process is None:
            return
        gracefully_kill(self._pw_process, timeout_seconds)

    def _start_pw_process(self) -> None:
        task_payload = dill.dumps(self)
        self._pw_process = multiprocessing.Process(
            target=_run_task_in_worker, args=(self.files_path, task_payload)
        )
        self._pw_process.start()

    def _pw_task_worker_function(self):
        watermark_store = WatermarkStore(self.watermark_path) if self.watermark_path else None
        if watermark_store is not None:
            self._resume_instant_watermark = watermark_store.read_instant_watermark()
            self._resume_window_watermark = watermark_store.read_window_watermark()

        table = self.input(**self.input_kwargs)
        instant_table, window_table = self.__construct_pw_dag(table)
        if watermark_store is not None:
            self.__subscribe_watermark(instant_table, window_table, watermark_store)

        if isinstance(self.output, TaskOutput):
            # TODO HERE WE NEED TO TAKE INTO ACCOUNT THE OPTIONS THAT THE TaskOutput class supports
            # WE NEED TO COMPUTE THE failed table, valid ones, etc and also provide a better
            # way for the user to provide output kwargs, ideally output kwargs dictionary per
            # available option
            self.output(instant_table, **self.output_kwargs)
        elif isinstance(self.output, Callable):
            if instant_table:
                self.output(instant_table, **self.output_kwargs)
            if window_table:
                if "filename" in self.output_kwargs:
                    p = Path(self.output_kwargs["filename"])
                    window_filename = str(p.parent / f"{p.stem}_window{p.suffix}")
                    window_kwargs = {**self.output_kwargs, "filename": window_filename}
                elif "topic_name" in self.output_kwargs:
                    window_kwargs = {
                        **self.output_kwargs,
                        "topic_name": f"{self.output_kwargs['topic_name']}_window",
                    }
                elif "topic" in self.output_kwargs:
                    window_kwargs = {
                        **self.output_kwargs,
                        "topic": f"{self.output_kwargs['topic']}_window",
                    }
                elif "table_name" in self.output_kwargs:
                    window_kwargs = {
                        **self.output_kwargs,
                        "table_name": f"{self.output_kwargs['table_name']}_window",
                    }
                else:
                    window_kwargs = dict(self.output_kwargs)
                self.output(window_table, **window_kwargs)

        try:
            pw.run(monitoring_level=pw.MonitoringLevel.NONE, default_logging=False)
        finally:
            if watermark_store is not None:
                watermark_store.close()

    def __subscribe_watermark(
        self,
        instant_table: pw.Table | None,
        window_table: pw.Table | None,
        watermark_store: WatermarkStore,
    ) -> None:
        if instant_table is not None and self.windowby_column:
            self.__subscribe_instant_watermark(instant_table, watermark_store)

        if window_table is not None and self.include_window_bounds:
            self.__subscribe_window_watermark(window_table, watermark_store)

    def __subscribe_instant_watermark(
        self,
        instant_table: pw.Table,
        watermark_store: WatermarkStore,
    ) -> None:
        windowby_column = self.windowby_column

        def on_instant(key, row, time, is_addition):
            if is_addition:
                watermark_store.advance_instant_to(int(row[windowby_column]))

        pw.io.subscribe(instant_table, on_instant)

    def __subscribe_window_watermark(
        self,
        window_table: pw.Table,
        watermark_store: WatermarkStore,
    ) -> None:
        def on_window(key, row, time, is_addition):
            if is_addition:
                watermark_store.advance_window_to(int(row[WINDOW_END_COLUMN_NAME]))

        pw.io.subscribe(window_table, on_window)

    def __construct_pw_dag(self, table: pw.Table) -> pw.Table:
        self.instant_table = self.__construct_instant_pw_dag(table) if self.instant_checks else None
        self.window_table = self.__construct_window_pw_dag(table) if self.window_checks else None
        return self.instant_table, self.window_table

    def __construct_instant_pw_dag(self, table: pw.Table) -> pw.Table:
        # Set the instant checks watermark (if any)
        if self._resume_instant_watermark is not None and self.windowby_column:
            table = table.filter(table[self.windowby_column] >= self._resume_instant_watermark)

        # Construct instant checks
        kwargs: dict[str, pw.ColumnExpression] = dict()
        for instant_check in self.instant_checks:
            kwargs[instant_check.name] = instant_check.get_measurement_expression()
        assessment_table = table.with_columns(**kwargs)

        # Append streamdaq metadata as JSON (if user has opted in)
        return self.__add_streamdaq_metadata(assessment_table)

    def __add_streamdaq_metadata(self, table: pw.Table) -> pw.Table:
        if self.include_streamdaq_metadata:
            return table.with_columns(
                _streamdaq_metadata=pw.Json({"task_name": self.name, "task_version": self.version})
            )
        return table

    def __collect_reduce_measurement_assessment_kwargs(
        self,
    ) -> tuple[dict[str, pw.ColumnExpression]]:
        reduce_kwargs: dict[str, pw.ColumnExpression] = dict()
        measurement_kwargs: dict[str, pw.ColumnExpression] = dict()
        assessment_kwargs: dict[str, pw.ColumnExpression] = dict()

        reduce_kwargs = (
            {}
            if not self.include_window_bounds
            else {
                WINDOW_START_COLUMN_NAME: pw.this._pw_window_start,
                WINDOW_END_COLUMN_NAME: pw.this._pw_window_end,
            }
        )

        for window_check in self.window_checks:
            # collect reduce kwargs
            reduce_kwargs = {
                **reduce_kwargs,
                **window_check.get_reduce_kwargs(),
            }

            # collect measurement kwargs
            measurement_expression = window_check.get_measurement_expression()
            if measurement_expression is not None:
                measurement_kwargs[window_check.name] = measurement_expression

            # collect assessment kwargs
            assessment_expression = window_check.get_assessment_expression()
            if assessment_expression is not None:
                assessment_kwargs[window_check.name] = assessment_expression

        return reduce_kwargs, measurement_kwargs, assessment_kwargs

    def __cleanup_window_pw_dag_columns(
        self,
        table: pw.Table,
        reduce_kwargs: dict[str, pw.ColumnExpression],
        measurement_kwargs: dict[str, pw.ColumnExpression],
        assessment_kwargs: dict[str, pw.ColumnExpression],
    ) -> pw.Table:
        all_columns = set(reduce_kwargs.keys())
        all_columns.update(set(measurement_kwargs.keys()))
        all_columns.update(set(assessment_kwargs.keys()))
        columns_to_remove = [
            column
            for column in all_columns
            if column.startswith(DataQualityMeasure._streamdaq_internal_prefix)
        ]
        return table.without(*columns_to_remove)

    def __construct_window_pw_dag(self, table: pw.Table) -> pw.Table:
        # Collect all kwargs for reduce, measurement, and assessment
        reduce_kwargs, measurement_kwargs, assessment_kwargs = (
            self.__collect_reduce_measurement_assessment_kwargs()
        )

        # Collect the window checks watermark (if any)
        watermark_aware_window = (
            self.window
            if self._resume_window_watermark is None
            else dataclasses.replace(self.window, origin=self._resume_window_watermark)
        )

        # Construct the pathway DAG
        reduced = table.windowby(
            table[self.windowby_column],
            window=watermark_aware_window,
            behavior=pw.temporal.exactly_once_behavior(shift=self.wait_for_late),
        ).reduce(**reduce_kwargs)
        measurements_table = reduced.with_columns(**measurement_kwargs)
        assessments_table = measurements_table.with_columns(**assessment_kwargs)

        # Cleanup streamdaq-internal, intermediate columns
        assessments_table = self.__cleanup_window_pw_dag_columns(
            assessments_table,
            reduce_kwargs,
            measurement_kwargs,
            assessment_kwargs,
        )

        return self.__add_streamdaq_metadata(assessments_table)
