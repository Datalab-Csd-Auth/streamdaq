import operator
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Literal

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
