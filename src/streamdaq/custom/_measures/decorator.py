from collections.abc import Callable
from typing import Any

from streamdaq.measures.custom import CustomDataQualityMeasure
from streamdaq.utils.picklable import Lambda


def measure(
    columns: list[str],
    name: str | None = None,
    sort_by_column: str | None = None,
    desc: bool = False,
):
    """Decorator that converts a function into a custom streamdaq data quality measure."""

    def decorator(func: Callable[[dict[str, list[Any]]], Any]) -> type[CustomDataQualityMeasure]:
        custom_measure_name = name or func.__name__

        class_dict = {
            "name": custom_measure_name,
            "columns": columns,
            "measurement_function": staticmethod(Lambda(func)),
            "sort_by_column": sort_by_column,
            "desc": desc,
            "__doc__": func.__doc__,
            "__module__": func.__module__,
        }
        return type(custom_measure_name, (CustomDataQualityMeasure,), class_dict)

    return decorator
