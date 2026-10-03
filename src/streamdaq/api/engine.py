from streamdaq.api.models import TaskConfig
from streamdaq.checks import WindowDataQualityCheck
from streamdaq.checks.registry import INSTANT_CHECK_REGISTRY
from streamdaq.io.sinks.registry import SINK_REGISTRY
from streamdaq.io.sources.registry import SOURCE_REGISTRY
from streamdaq.measures.registry import MEASURE_REGISTRY
from streamdaq.tasks.base import Task
from streamdaq.temporal.windows.registry import WINDOW_REGISTRY


def build_task(config: TaskConfig) -> Task:
    """
    Translates an API TaskConfig model into a StreamDAQ Task object.
    """
    task = Task(
        **{
            **config.task_kwargs,
            "input": SOURCE_REGISTRY[config.input.type](config.input.params),
            "output": SINK_REGISTRY[config.output.type],
        }
    )

    # Add Instant Checks
    instant_checks = []
    for instant_check in config.instant_checks:
        check_class = INSTANT_CHECK_REGISTRY[instant_check.check_class]
        instant_checks.append(check_class(name=instant_check.name, **instant_check.params))

    if instant_checks:
        task.add_instant_checks(*instant_checks)

    # Add Window Checks
    if config.window_checks_config:
        window_checks_config = config.window_checks_config
        window_func = WINDOW_REGISTRY[window_checks_config.window.type]
        window = window_func(**window_checks_config.window.params)

        window_checks = []
        for window_check in window_checks_config.checks:
            measure_class = MEASURE_REGISTRY[window_check.measure.type]
            measure = measure_class(**window_check.measure.params)
            window_checks.append(
                WindowDataQualityCheck(window_check.name, measure, window_check.must_be)
            )

        task.add_window_checks(*window_checks, window=window)

    return task
