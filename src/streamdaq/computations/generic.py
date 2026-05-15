import operator
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Literal

from streamdaq.utils.correlation_method import CorrelationMethod, correlation_method_to_function_map
from streamdaq.utils.validation import ensure_iterable


def set_conformance_count(
    elements: Iterable[int | float | str],
    allowed_values: Iterable[int | float | str],
) -> int:
    elements = ensure_iterable(elements)
    allowed_values = set(ensure_iterable(allowed_values))
    return sum(element in allowed_values for element in elements)


def most_frequent_elements(
    elements: Iterable[int | float | str],
) -> tuple[int | float | str, ...]:
    elements = ensure_iterable(elements)
    counts = Counter(elements)
    if not counts:
        return ()
    max_freq = max(counts.values())
    return tuple(elem for elem, freq in counts.items() if freq == max_freq)


def compute_constancy(
    elements: Iterable[int | float | str],
) -> int:
    elements = ensure_iterable(elements)
    counts = Counter(elements)
    if not counts:
        return 0
    return counts.most_common(1)[0][1]


def count_singletons(
    elements: Iterable[int | float | str],
) -> int:
    elements = ensure_iterable(elements)
    counts = Counter(elements)
    return sum(1 for count in counts.values() if count == 1)


def is_monotonic(
    elements: Iterable[int | float | str],
    direction: Literal["asc", "desc"] = "asc",
    strict: bool = True,
) -> bool:
    if direction not in ("asc", "desc"):
        raise ValueError(f"direction must be 'asc' or 'desc', got {direction!r}")

    comparator_map: dict[
        tuple[Literal["asc", "desc"], bool], Callable[[int | float | str, int | float | str], bool]
    ] = {
        ("asc", True): operator.lt,
        ("asc", False): operator.le,
        ("desc", True): operator.gt,
        ("desc", False): operator.ge,
    }
    compare = comparator_map[(direction, strict)]

    iterator = iter(ensure_iterable(elements))
    try:
        prev = next(iterator)
    except StopIteration:
        return True

    if isinstance(prev, float) and prev != prev:
        return False

    for current in iterator:
        if isinstance(current, float) and current != current:
            return False
        if not compare(prev, current):
            return False
        prev = current
    return True


def calculate_correlation(
    x, y, method: CorrelationMethod | str = CorrelationMethod.PEARSON, precision: int | None = None
) -> float:
    """
    Computes the correlation/association between x and y, rounded to the specified precision.

    :param x: the x array_like values
    :param y: the y array_like values
    :param precision: the number of decimal places to include in the result
    :return: the selected correlation coefficient
    """
    try:
        x, y = ensure_iterable(x), ensure_iterable(y)
        if method not in correlation_method_to_function_map:
            raise NotImplementedError(
                f"Correlation method `{method}` is not implemented yet. "
                f"Please use one of {list(correlation_method_to_function_map.keys())}."
            )
        correlation_function = correlation_method_to_function_map[method]
        result = correlation_function(x, y)
        if precision is None:
            return result
        return round(result, precision)
    except ValueError:
        # If the input arrays are empty or have different lengths, scipy will raise a ValueError
        return float("nan")
