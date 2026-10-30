# :white_check_mark: Assessments

An assessment decides whether a value is good. It's given as `must_be`, which is applied in both [window checks](window-checks.md) and [instant checks](instant-checks.md). The result column then holds `True` or `False`.

`must_be` can be written in four ways.

## Comparisons

An operator followed by a number:

| `must_be` | `True` when the value is |
|---|---|
| `">= 5"` | at least 5 |
| `"> 5"` | more than 5 |
| `"<= 5"` | at most 5 |
| `"< 5"` | less than 5 |
| `"== 5"` | exactly 5 |

Spaces are optional (`">=5"` works too), and decimals are allowed (`"<= 0.25"`).

!!! note
    There's no "not equal" operator. Use a function (below) for `value != 5`.

## Ranges

Two numbers in brackets. A square bracket includes the bound, a round bracket excludes it:

| `must_be` | `True` when the value is |
|---|---|
| `"[1, 5]"` | between 1 and 5, both included |
| `"(1, 5)"` | between 1 and 5, both excluded |
| `"[1, 5)"` | at least 1 and less than 5 |
| `"(5, 15]"` | more than 5 and at most 15 |

The lower bound must be smaller than the upper bound.

## Functions

Any function that takes the value and returns `True` or `False`:

```py
def is_seven_frequent(most_frequent: tuple) -> bool:
    return 7 in most_frequent


WindowDataQualityCheck("seven_is_common", MostFrequent("events"), is_seven_frequent)
```

Functions are useful for values that aren't single numbers, such as the tuple from `MostFrequent` or the dictionary from `Percentiles`.

## Registered assessments

An assessment registered with `@assessment` can be used by its **name**. This is how custom assessments are used from the [REST API](rest-api.md), where functions can't be sent:

```py
from streamdaq.custom import assessment


@assessment(name="IsWithinTolerance")
def is_within_tolerance(value: float) -> bool:
    return abs(value) <= 5


WindowDataQualityCheck("drop_ok", MaxDelta("temperature", time_column="timestamp"), "IsWithinTolerance")
```

See [Custom Code](custom-code.md#assessments). If a name is both registered and looks like a comparison or range, the registered assessment wins.

## Checking several conditions

A check has one `must_be`. To test several conditions on the same measure, add one check per condition:

```py
WindowDataQualityCheck("not_too_few", Count("temperature"), ">= 5"),
WindowDataQualityCheck("not_too_many", Count("temperature"), "<= 100"),
```

or combine them in one range (`"[5, 100]"`) or function.
