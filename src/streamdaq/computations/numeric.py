import math
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

import numpy as np

from streamdaq.utils.validation import ensure_iterable


def _count_integer_digits(number: int | float) -> int:
    if not np.isfinite(number):
        raise ValueError(f"Cannot count digits in non-finite value: {number}")
    abs_int = abs(int(number))
    return 1 if abs_int == 0 else len(str(abs_int))


def is_greater_than(a: int | float, b: int | float, or_equal: bool = False) -> bool:
    return a >= b if or_equal else a > b


def fraction(
    numerator: int | float,
    denominator: int | float,
    precision: int | None = None,
) -> float:
    if denominator == 0:
        raise ZeroDivisionError("denominator must not be zero")
    result = numerator / denominator
    if precision is None:
        return result
    return round(result, precision)


def range_conformance_count(
    elements: Iterable[int | float],
    low: int | float,
    high: int | float,
    inclusive_low: bool = False,
    inclusive_high: bool = False,
) -> int:
    if low > high:
        raise ValueError(f"low ({low}) must be <= high ({high})")
    elements = np.asarray(ensure_iterable(elements), dtype=np.float64)
    low, high = np.float64(low), np.float64(high)

    above_low = (elements >= low) if inclusive_low else (elements > low)
    below_high = (elements <= high) if inclusive_high else (elements < high)
    return int((above_low & below_high).sum())


def percentiles_dict(
    elements: Iterable[int | float],
    percentiles: Iterable[int | float],
    precision: int | None = None,
) -> dict[int | float, int | float]:
    elements = ensure_iterable(elements)
    percentiles = ensure_iterable(percentiles)
    results = np.percentile(elements, percentiles)

    if precision is not None:
        results = np.round(results, precision)

    return dict(zip(percentiles, results))


def first_digit(elements: Iterable[int | float]) -> list[int]:
    elements = ensure_iterable(elements)
    result = []
    for number in elements:
        if not np.isfinite(number):
            raise ValueError(f"Cannot extract first digit from {number}")
        if number == 0:
            result.append(0)
        else:
            result.append(int(f"{abs(number):.15e}"[0]))
    return result


def integer_part(elements: Iterable[int | float]) -> list[int]:
    elements = ensure_iterable(elements)
    return [int(number) for number in elements]


def fractional_part(elements: Iterable[int | float]) -> list[int]:
    elements = ensure_iterable(elements)
    results = []
    for number in elements:
        if not np.isfinite(number):
            raise ValueError(f"Cannot extract fractional part from {number}")
        d = Decimal(str(abs(number)))
        sign, digits, exponent = d.as_tuple()
        if exponent >= 0:
            results.append(0)
        else:
            frac_digits = "".join(map(str, digits[exponent:]))
            results.append(int(frac_digits) if frac_digits else 0)
    return results


def digit_count(elements: Iterable[int | float]) -> list[int]:
    elements = ensure_iterable(elements)
    return [_count_integer_digits(number) for number in elements]


def integer_part_digit_count(elements: Iterable[int | float]) -> list[int]:
    elements = ensure_iterable(elements)
    return [_count_integer_digits(number) for number in elements]


def fractional_part_digit_count(elements: Iterable[int | float]) -> list[int]:
    elements = ensure_iterable(elements)
    results = []
    for number in elements:
        if not np.isfinite(number):
            raise ValueError(f"Cannot count digits in non-finite value: {number}")
        d = Decimal(str(abs(number))).normalize()
        sign, digits, exponent = d.as_tuple()
        results.append(max(0, -exponent))
    return results


def first_digit_frequencies(
    elements: Iterable[int | float],
    precision: int | None = None,
) -> dict[int, tuple[int, float]]:
    digits = first_digit(elements)
    total = len(digits)
    freq: dict[int, tuple[int, float]] = {}
    for d in range(10):
        abs_count = digits.count(d)
        rel_freq = abs_count / total if total > 0 else 0.0
        if precision is not None:
            rel_freq = round(rel_freq, precision)
        freq[d] = (abs_count, rel_freq)
    return freq


def filter_numeric(
    elements: Iterable[Any],
    *,
    allow_nan: bool = False,
    allow_inf: bool = False,
) -> list[float]:
    elements = ensure_iterable(elements)
    result: list[float] = []
    for element in elements:
        if isinstance(element, (bool, np.bool_)):
            continue
        try:
            value = float(element)
        except (ValueError, TypeError):
            continue
        if not allow_nan and math.isnan(value):
            continue
        if not allow_inf and math.isinf(value):
            continue
        result.append(value)
    return result


def linear_slope(
    values: Iterable[int | float],
    timestamps: Iterable[int | float],
    *,
    precision: int | None = None,
) -> float:
    values_list = list(ensure_iterable(values))
    timestamps_list = list(ensure_iterable(timestamps))
    if len(values_list) != len(timestamps_list):
        raise ValueError(
            f"values and timestamps must have same length, "
            f"got {len(values_list)} and {len(timestamps_list)}"
        )
    if len(values_list) < 2:
        return 0.0

    x = np.array(timestamps_list, dtype=np.float64)
    y = np.array(values_list, dtype=np.float64)
    x = x - x.min()

    denominator = np.sum((x - np.mean(x)) ** 2)
    if denominator == 0:
        return 0.0

    coefficients = np.polyfit(x, y, 1)
    slope = float(coefficients[0])
    if precision is not None:
        return round(slope, precision)
    return slope
