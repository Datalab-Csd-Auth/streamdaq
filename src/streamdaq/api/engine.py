import pathway as pw

from streamdaq.api.models import TaskConfig
from streamdaq.checks import InRange, WindowDataQualityCheck
from streamdaq.measures import InRangeCount, Mean
from streamdaq.sessions.base import Session
from streamdaq.tasks.base import Task

# Registry dictionaries
INPUT_REGISTRY = {
    "markdown_table": lambda params: lambda **kwargs: pw.debug.table_from_markdown(params["markdown"])
}

OUTPUT_REGISTRY = {
    "jsonlines": pw.io.jsonlines.write
}

INSTANT_CHECK_REGISTRY = {
    "InRange": InRange
}

MEASURE_REGISTRY = {
    "Mean": Mean,
    "InRangeCount": InRangeCount
}

WINDOW_REGISTRY = {
    "sliding": pw.temporal.sliding
}

class EngineManager:
    """
    Manages the translation of API configuration models into Pathway objects
    and handles the lifecycle of the StreamDAQ session.
    """
    def __init__(self):
        self.session: Session | None = None

    def apply_tasks(self, task_configs: list[TaskConfig]):
        # Terminate any running tasks from the previous session state
        if self.session:
            for task in self.session.tasks:
                if task._pw_process and task._pw_process.is_alive():
                    task._pw_process.terminate()
                    task._pw_process.join()

        if not task_configs:
            self.session = None
            return

        tasks = []
        for config in task_configs:
            # Build Input
            input_callable = INPUT_REGISTRY[config.input.type](config.input.params)
            
            # Build Output
            output_callable = OUTPUT_REGISTRY[config.output.type]

            task = Task(
                name=config.name,
                input=input_callable,
                output=output_callable,
                output_kwargs=config.output.params,
                windowby_column=config.windowby_column
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

            tasks.append(task)

        # Start the new session
        self.session = Session(tasks=tasks, name="api_managed_session")
        self.session.start()

# Global singleton to manage state across API requests
engine = EngineManager()
