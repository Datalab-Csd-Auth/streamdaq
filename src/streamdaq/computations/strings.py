import re
from collections.abc import Iterable

from streamdaq.utils.validation import ensure_iterable


def strings_to_length(elements: Iterable[str]) -> list[int]:
    elements = ensure_iterable(elements)
    return [len(str(s)) for s in elements]


def regex_conformance_count(
    elements: Iterable[str],
    regex: str,
) -> int:
    elements = ensure_iterable(elements)
    pattern = re.compile(regex)
    return sum(pattern.match(element) is not None for element in elements)
