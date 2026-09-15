from collections.abc import Callable


def _parse_range_expression(expr: str) -> tuple[str, float, float] | None:
    """
    Parse a range expression and return the brackets and numbers.

    Args:
        expr (str): Expression like "[1,5]" or "(2.5,10)"

    Returns:
        Optional[tuple[str, float, float]]: Tuple of (brackets, lower_bound, upper_bound)
        or None if invalid
    """
    import re

    # Regular expression to match range patterns
    range_pattern = r"^[\(\[]([-+]?\d*\.?\d+)\s*,\s*([-+]?\d*\.?\d+)[\)\]]$"

    match = re.match(range_pattern, expr.strip())
    if not match:
        return None

    try:
        # Extract brackets
        brackets = expr[0] + expr[-1]
        # Extract numbers
        lower_bound = float(match.group(1))
        upper_bound = float(match.group(2))

        if lower_bound >= upper_bound:
            print("Invalid range: lower bound must be less than upper bound")
            # TODO ADD LOGGER!
            return None

        return brackets, lower_bound, upper_bound
    except ValueError:
        return None


def _create_comparison_lambda(operator: str, threshold: float) -> Callable[[float], bool]:
    """
    Create a lambda function for simple comparison operations.

    Args:
        operator (str): Comparison operator
        threshold (float): Number to compare against

    Returns:
        Callable[[float], bool]: Lambda function implementing the comparison
    """
    operator_map = {
        ">=": lambda x: x >= threshold,
        "<=": lambda x: x <= threshold,
        "==": lambda x: x == threshold,
        ">": lambda x: x > threshold,
        "<": lambda x: x < threshold,
    }

    return operator_map.get(operator, lambda x: True)


def _create_range_lambda(brackets: str, lower: float, upper: float) -> Callable[[float], bool]:
    """
    Create a lambda function for range comparisons.

    Args:
        brackets (str): String containing the bracket types (e.g., '[]', '()')
        lower (float): Lower bound
        upper (float): Upper bound

    Returns:
        Callable[[float], bool]: Lambda function implementing the range check
    """
    left_bracket, right_bracket = brackets[0], brackets[1]

    def range_check(x: float) -> bool:
        left_compare = x >= lower if left_bracket == "[" else x > lower
        right_compare = x <= upper if right_bracket == "]" else x < upper
        return left_compare and right_compare

    return range_check


def _parse_comparison_operator(expr: str) -> tuple[str, float] | None:
    """
    Parse a string containing a comparison operator and a number.
    Returns tuple of (operator, number) if valid, None otherwise.

    Args:
        expr (str): Expression like ">=10" or "<5.5"

    Returns:
        Optional[tuple[str, float]]: Tuple of (operator, number) or None if invalid
    """
    # Define valid operators
    valid_operators = [">=", "<=", "==", ">", "<"]

    # Try to match the pattern: operator followed by number
    for op in valid_operators:
        if op in expr:
            try:
                number_str = expr.replace(op, "").strip()
                number = float(number_str)
                return op, number
            except ValueError:
                return None

    return None


def string_to_callable(expr: str) -> Callable:
    """
    Main function that creates a comparison function based on the input expression.

    Args:
        expr (str): Expression string (e.g., ">=10", "[1,5]")

    Returns:
        Callable[[float], bool]: Lambda function implementing the comparison
    """
    # Handle empty or invalid input
    if not expr or not isinstance(expr, str):
        raise ValueError(f"Cannot construct check function from `{expr}`.")

    # Remove whitespace
    expr = expr.strip()

    # Try parsing as simple comparison
    comparison_result = _parse_comparison_operator(expr)
    if comparison_result:
        operator, number = comparison_result
        return _create_comparison_lambda(operator, number)

    # Try parsing as range expression
    range_result = _parse_range_expression(expr)
    if range_result:
        brackets, lower, upper = range_result
        return _create_range_lambda(brackets, lower, upper)

    # If nothing matches, log warning and return identity function
    raise ValueError(f"Cannot construct check function from `{expr}`.")
