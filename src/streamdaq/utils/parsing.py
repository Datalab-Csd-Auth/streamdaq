import math
import re
from collections.abc import Callable
from typing import Literal, NamedTuple, cast


def extract_leading_integer(
    text: str,
    *,
    default: int = 0,
    strip_whitespace: bool = True,
) -> int:
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
    if strip_whitespace:
        text = text.lstrip()
    if not text:
        return default
    match = re.match(r"(\d+)", text)
    return int(match.group(1)) if match else default


ComparisonOperator = Literal["<", "<=", ">", ">=", "==", "!="]

_COMPARISON_PATTERN = re.compile(
    r"^\s*(<=|>=|!=|==|<|>)\s*"
    r"(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
    r"\s*$"
)


def parse_comparison_expr(
    expr: str,
) -> tuple[ComparisonOperator, float] | None:
    if not expr or not isinstance(expr, str):
        return None
    match = _COMPARISON_PATTERN.match(expr)
    if not match:
        return None
    operator = cast(ComparisonOperator, match.group(1))
    value = float(match.group(2))
    if not math.isfinite(value):
        return None
    return (operator, value)


class RangeExpr(NamedTuple):
    lower: float
    upper: float
    lower_inclusive: bool
    upper_inclusive: bool

    def contains(self, value: float) -> bool:
        if math.isnan(value):
            return False
        lower_ok = (value >= self.lower) if self.lower_inclusive else (value > self.lower)
        upper_ok = (value <= self.upper) if self.upper_inclusive else (value < self.upper)
        return lower_ok and upper_ok


_NUM = r"(-?(?:inf|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?))"
_RANGE_PATTERN = re.compile(
    r"^\s*"
    r"([\[\(])"
    r"\s*" + _NUM + r"\s*"
    r","
    r"\s*" + _NUM + r"\s*"
    r"([\]\)])"
    r"\s*$"
)


def parse_range_expr(expr: str) -> RangeExpr | None:
    if not expr or not isinstance(expr, str):
        return None
    match = _RANGE_PATTERN.match(expr)
    if not match:
        return None
    open_bracket, lower_str, upper_str, close_bracket = match.groups()
    lower = float(lower_str)
    upper = float(upper_str)
    if lower > upper:
        return None
    lower_inclusive = open_bracket == "["
    upper_inclusive = close_bracket == "]"
    if lower == upper and not (lower_inclusive and upper_inclusive):
        return None
    if math.isinf(lower):
        lower_inclusive = False
    if math.isinf(upper):
        upper_inclusive = False
    return RangeExpr(
        lower=lower,
        upper=upper,
        lower_inclusive=lower_inclusive,
        upper_inclusive=upper_inclusive,
    )


def make_comparison_predicate(
    operator: ComparisonOperator,
    threshold: int | float,
) -> Callable[[int | float], bool]:
    if not isinstance(threshold, (int, float)):
        raise TypeError(f"threshold must be numeric, got {type(threshold).__name__}")
    operator_map: dict[str, Callable[[int | float], bool]] = {
        ">=": lambda x: x >= threshold,
        "<=": lambda x: x <= threshold,
        "==": lambda x: x == threshold,
        "!=": lambda x: x != threshold,
        ">": lambda x: x > threshold,
        "<": lambda x: x < threshold,
    }
    if operator not in operator_map:
        valid_ops = ", ".join(sorted(operator_map.keys()))
        raise ValueError(f"Invalid operator '{operator}'. Valid operators: {valid_ops}")
    return operator_map[operator]


def make_range_predicate(
    lower: int | float,
    upper: int | float,
    inclusive_lower: bool = True,
    inclusive_upper: bool = True,
) -> Callable[[int | float], bool]:
    if not isinstance(lower, (int, float)) or not isinstance(upper, (int, float)):
        raise TypeError("lower and upper bounds must be numeric")
    if lower > upper:
        raise ValueError(f"lower bound ({lower}) must be <= upper bound ({upper})")
    if lower == upper and not (inclusive_lower and inclusive_upper):
        raise ValueError("Range with equal bounds requires both to be inclusive")

    def range_check(x: int | float) -> bool:
        if math.isnan(x):
            return False
        lower_ok = (x >= lower) if inclusive_lower else (x > lower)
        upper_ok = (x <= upper) if inclusive_upper else (x < upper)
        return lower_ok and upper_ok

    return range_check


def parse_threshold_expr(
    expression: str,
    *,
    strict: bool = True,
) -> Callable[[int | float], bool] | None:
    if not isinstance(expression, str):
        raise TypeError(f"expression must be a string, got {type(expression).__name__}")
    expr = expression.strip()
    if not expr:
        if strict:
            raise ValueError("expression cannot be empty")
        return None

    comparison_result = parse_comparison_expr(expr)
    if comparison_result:
        operator, value = comparison_result
        return make_comparison_predicate(operator, value)

    range_result = parse_range_expr(expr)
    if range_result:
        return make_range_predicate(
            range_result.lower,
            range_result.upper,
            range_result.lower_inclusive,
            range_result.upper_inclusive,
        )

    if strict:
        raise ValueError(f"Unable to parse expression: '{expression}'")
    return None
