from collections.abc import Callable
from typing import Any

from streamdaq.measures.custom import CustomDataQualityMeasure


def measure(
    columns: list[str],
    name: str | None = None,
    sort_by_column: str | None = None,
    desc: bool = False,
):
    """Decorator that converts a function into a custom streamdaq data quality measure."""

    def decorator(func: Callable[[dict[str, list[Any]]], Any]) -> type[CustomDataQualityMeasure]:
        custom_measure_name = name or func.__name__

        def __init__(self, **kwargs):
            final_kwargs = {
                "name": custom_measure_name,
                "columns": columns,
                "measurement_function": func,
                "sort_by_column": sort_by_column,
                "desc": desc,
            }
            final_kwargs.update(kwargs)
            CustomDataQualityMeasure.__init__(self, **final_kwargs)

        class_dict = {
            "__init__": __init__,
            "__doc__": func.__doc__,
            "__module__": func.__module__,
        }

        return type(custom_measure_name, (CustomDataQualityMeasure,), class_dict)

    return decorator
