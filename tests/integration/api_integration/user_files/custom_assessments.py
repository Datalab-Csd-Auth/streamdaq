"""Custom assessment predicates exercised by the api_integration suite.

Loaded into the running API through ``--files`` so measures whose output is not a
scalar (tuples, dicts, ndarrays) can still be checked end to end. Each predicate reads
the measure's real output type and is chosen to hold in some windows of the fixed stream
and fail in others, so every window check flips between ``true`` and ``false`` across the run.
"""

import numpy as np
import pathway as pw

from streamdaq.custom import assessment


@assessment()
def has_enough_samples(values: tuple) -> bool:
    return len(values) >= 3


@assessment()
def value_span_at_least_50(sorted_values: tuple) -> bool:
    return bool(sorted_values) and sorted_values[-1] - sorted_values[0] >= 50


@assessment()
def ends_higher_than_it_starts(time_sorted_values: tuple) -> bool:
    return bool(time_sorted_values) and time_sorted_values[-1] > time_sorted_values[0]


@assessment()
def has_positive_jump(deltas: tuple) -> bool:
    return bool(deltas) and max(deltas) >= 30


@assessment()
def leading_digit_one_present(first_digit_freqs: pw.Json) -> bool:
    count, _relative_frequency = first_digit_freqs.as_dict()["1"]
    return count >= 1


@assessment()
def median_at_least_20(percentiles: pw.Json) -> bool:
    return percentiles.as_dict()["50"] >= 20


@assessment()
def array_max_at_least_100(values: np.ndarray) -> bool:
    return values.size > 0 and float(values.max()) >= 100


@assessment()
def contains_ok(most_frequent: tuple) -> bool:
    return "OK" in most_frequent
