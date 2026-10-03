"""Tests for the API-to-engine translation layer (``engine.build_task``).

``build_task`` converts a declarative ``TaskConfig`` into a concrete ``Task`` by
resolving each named component through the real registries. These tests use real
registries and real config objects; the CSV source is not invoked, so nothing
touches the network.
"""

from streamdaq.api.engine import build_task
from streamdaq.api.models import (
    InputConfig,
    InstantCheckConfig,
    MeasureConfig,
    OutputConfig,
    TaskConfig,
    WindowCheckConfig,
    WindowChecksConfig,
    WindowConfig,
)
from streamdaq.checks.instant.any_column.in_range import InRange
from streamdaq.io.sources.csv_source import CsvSource
from streamdaq.measures.numeric.mean import Mean


def _full_config_kwargs(**overrides):
    """Return the kwargs for a complete, startable ``TaskConfig`` (overridable per test)."""
    kwargs = dict(
        name="my_task",
        windowby_column="ts",
        input=InputConfig(type="csv", params={"path": "/tmp/data.csv"}),
        output=OutputConfig(type="jsonlines", params={"filename": "out.jsonl"}),
        instant_checks=[
            InstantCheckConfig(
                name="age_in_range",
                check_class="InRange",
                params={"column": "age", "low": 0, "high": 120},
            )
        ],
        window_checks_config=WindowChecksConfig(
            window=WindowConfig(type="tumbling", params={"duration": 5}),
            checks=[
                WindowCheckConfig(
                    name="mean_ok",
                    measure=MeasureConfig(type="Mean", params={"column": "age"}),
                    must_be="[0, 100]",
                )
            ],
        ),
    )
    kwargs.update(overrides)
    return kwargs


class TestBuildTaskBasics:
    def test_sets_name_and_windowby_column(self):
        config = TaskConfig(**_full_config_kwargs())
        task = build_task(config)
        assert task.name == "my_task"
        assert task.windowby_column == "ts"

    def test_input_is_resolved_to_a_callable(self):
        config = TaskConfig(**_full_config_kwargs())
        task = build_task(config)
        assert isinstance(task.input, CsvSource)
        assert callable(task.input)

    def test_output_callable_and_kwargs_are_wired(self):
        config = TaskConfig(**_full_config_kwargs())
        task = build_task(config)
        assert callable(task.output)
        assert task.output_kwargs == {"filename": "out.jsonl"}


class TestBuildTaskChecks:
    def test_instant_check_is_instantiated_from_registry(self):
        config = TaskConfig(**_full_config_kwargs())
        task = build_task(config)
        assert len(task.instant_checks) == 1
        check = task.instant_checks[0]
        assert isinstance(check, InRange)
        assert check.name == "age_in_range"

    def test_window_check_measure_is_instantiated(self):
        config = TaskConfig(**_full_config_kwargs())
        task = build_task(config)
        assert len(task.window_checks) == 1
        window_check = task.window_checks[0]
        assert window_check.name == "mean_ok"
        assert isinstance(window_check.measure, Mean)
        assert window_check.measure.column == "age"

    def test_window_is_set(self):
        config = TaskConfig(**_full_config_kwargs())
        task = build_task(config)
        assert task.window is not None


class TestBuildTaskOptionalSections:
    def test_no_instant_checks_when_omitted(self):
        config = TaskConfig(**_full_config_kwargs(instant_checks=[]))
        task = build_task(config)
        assert task.instant_checks == []

    def test_no_window_checks_when_config_absent(self):
        # An instant-only task: instant checks present, no windowby column, no window config
        config = TaskConfig(**_full_config_kwargs(windowby_column=None, window_checks_config=None))
        task = build_task(config)
        assert task.window_checks == []
        assert task.window is None


class TestBuildTaskWindowBounds:
    def test_include_window_bounds_defaults_to_true(self):
        config = TaskConfig(**_full_config_kwargs())
        task = build_task(config)
        assert task.include_window_bounds is True

    def test_include_window_bounds_false_is_passed_to_task(self):
        config = TaskConfig(**_full_config_kwargs(include_window_bounds=False))
        task = build_task(config)
        assert task.include_window_bounds is False


class TestBuildTaskWaitForLate:
    def test_wait_for_late_is_passed_to_task(self):
        config = TaskConfig(**_full_config_kwargs(wait_for_late=5))
        task = build_task(config)
        assert task.wait_for_late == 5

    def test_wait_for_late_defaults_to_none(self):
        config = TaskConfig(**_full_config_kwargs())
        task = build_task(config)
        assert task.wait_for_late is None
