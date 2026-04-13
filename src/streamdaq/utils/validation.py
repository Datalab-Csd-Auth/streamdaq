from collections.abc import Iterable
from typing import Any


def ensure_iterable(elements: Iterable[Any] | int | float | str) -> Iterable[Any]:
    if elements is None:
        raise TypeError("Input cannot be None; expected an iterable or scalar value")
    if isinstance(elements, str):
        return (elements,)
    try:
        iter(elements)
        return elements
    except TypeError:
        return (elements,)
