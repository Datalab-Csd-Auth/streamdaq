import multiprocessing
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

import pathway as pw

from streamdaq.checks.base import DataQualityCheck
from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.checks.window.base import WindowDataQualityCheck
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.tasks.task_output import TaskOutput
from streamdaq.utils.picklable import Lambda
from streamdaq.utils.ui import _is_ui_up
from streamdaq.windows.base import Window


@dataclass
class Task:
    input: Callable[[Any], pw.Table]
    output: Callable[[Any], None] | TaskOutput
    name: str | None = None
    instant_checks: list[InstantDataQualityCheck] = field(default_factory=Lambda(lambda: []))
    window_checks: list[WindowDataQualityCheck] = field(default_factory=Lambda(lambda: []))
    window: Window | None = None
    windowby_column: str | None = None
    input_kwargs: dict[str, Any] = field(default_factory=Lambda(lambda: {}))
    output_kwargs: dict[str, Any] = field(default_factory=Lambda(lambda: {}))

    def __post_init__(self):
        self.instant_table: pw.Table | None = None
        self.window_table: pw.Table | None = None
        self._pw_process: multiprocessing.Process | None = None

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

    def _start_pw_process(self) -> multiprocessing.Process:
        self._pw_process = multiprocessing.Process(target=self._pw_task_worker_function)
        self._pw_process.start()

    def _pw_task_worker_function(self):
        table = self.input(**self.input_kwargs)

        instant_table, window_table = self.__construct_pw_dag(table)
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
        else:
            ...
            # TODO PROBABLY WE NEED TO CHECK THAT THE OUTPUT IS VALID IN THE POST INIT
            # so that it is earlier than here

        # --- STREAMDAQ INTERNAL MONITORING (TEE PATTERN) ---
        if _is_ui_up():
            os.makedirs(".streamdaq_monitoring", exist_ok=True)
            task_id = self.name or "unnamed"
            if instant_table:
                pw.io.jsonlines.write(
                    instant_table, f".streamdaq_monitoring/{task_id}_instant.jsonl"
                )
            if window_table:
                pw.io.jsonlines.write(window_table, f".streamdaq_monitoring/{task_id}_window.jsonl")

        pw.run()

    def __construct_pw_dag(self, table: pw.Table) -> pw.Table:
        self.instant_table = self.__construct_instant_pw_dag(table) if self.instant_checks else None
        self.window_table = self.__construct_window_pw_dag(table) if self.window_checks else None
        return self.instant_table, self.window_table

    def __construct_instant_pw_dag(self, table: pw.Table) -> pw.Table:
        kwargs: dict[str, pw.ColumnExpression] = dict()
        for instant_check in self.instant_checks:
            kwargs[instant_check.name] = instant_check.get_measurement_expression()
        assessment_table = table.with_columns(**kwargs)
        return assessment_table

    def __collect_reduce_measurement_assessment_kwargs(
        self,
    ) -> tuple[dict[str, pw.ColumnExpression]]:
        reduce_kwargs: dict[str, pw.ColumnExpression] = dict()
        measurement_kwargs: dict[str, pw.ColumnExpression] = dict()
        assessment_kwargs: dict[str, pw.ColumnExpression] = dict()

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
        print(f"{all_columns=}, {columns_to_remove=}")
        return table.without(*columns_to_remove)

    def __construct_window_pw_dag(self, table: pw.Table) -> pw.Table:
        # First, collect all kwargs for reduce, measurement, and assessment
        reduce_kwargs, measurement_kwargs, assessment_kwargs = (
            self.__collect_reduce_measurement_assessment_kwargs()
        )

        print(f"{reduce_kwargs=}")
        print(f"{measurement_kwargs=}")
        print(f"{assessment_kwargs=}")

        # Then, use the kwargs to construct the pathway DAG
        reduced = table.windowby(
            table[self.windowby_column],
            # window=self.window.to_pathway_window(), TODO FIX THIS
            window=self.window,
            behavior=pw.temporal.exactly_once_behavior(),
        ).reduce(**reduce_kwargs)
        measurements_table = reduced.with_columns(**measurement_kwargs)
        assessments_table = measurements_table.with_columns(**assessment_kwargs)

        # Finally, cleanup streamdaq-internal, intermediate columns
        assessments_table = self.__cleanup_window_pw_dag_columns(
            assessments_table,
            reduce_kwargs,
            measurement_kwargs,
            assessment_kwargs,
        )

        return assessments_table
