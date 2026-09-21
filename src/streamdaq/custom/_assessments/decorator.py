from collections.abc import Callable
from typing import Any

from streamdaq.assessments.registry import ASSESSMENT_REGISTRY
from streamdaq.utils.picklable import Lambda


def assessment(name: str | None = None):
    """Registers the decorated function as a custom streamdaq data quality assessment predicate."""

    def decorator(func: Callable[[Any], bool]) -> Callable[[Any], bool]:
        assessment_name = name or func.__name__
        ASSESSMENT_REGISTRY[assessment_name] = Lambda(func)
        return func

    return decorator
