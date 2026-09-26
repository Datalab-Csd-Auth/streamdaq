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
    # Build Input
    input_callable = SOURCE_REGISTRY[config.input.type](config.input.params)

    # Build Output
    output_callable = SINK_REGISTRY[config.output.type]

    task = Task(
        name=config.name,
        input=input_callable,
        output=output_callable,
        output_kwargs=config.output.params,
        windowby_column=config.windowby_column,
    )

    # Add Instant Checks
    instant_checks = []
    for ic in config.instant_checks:
        check_class = INSTANT_CHECK_REGISTRY[ic.check_class]
        instant_checks.append(check_class(name=ic.name, **ic.params))

    if instant_checks:
        task.add_instant_checks(*instant_checks)

    # Add Window Checks
    if config.window_checks_config:
        wc_config = config.window_checks_config
        window_func = WINDOW_REGISTRY[wc_config.window.type]
        window = window_func(**wc_config.window.params)

        window_checks = []
        for wc in wc_config.checks:
            measure_class = MEASURE_REGISTRY[wc.measure.type]
            measure = measure_class(**wc.measure.params)
            window_checks.append(WindowDataQualityCheck(wc.name, measure, wc.must_be))

        task.add_window_checks(*window_checks, window=window)

    return task
