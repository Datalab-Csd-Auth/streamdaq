# :mag: Instant Checks

Instant checks are applied to **every row** as it arrives. Each check adds one `True`/`False` column, named after the check, to the per-row results, next to all the input columns.

```py
from streamdaq.checks import InRange, InSet, Regex

task.add_instant_checks(
    InRange(name="valid_temperature", column="temperature", low=-30, high=50),
    InSet(name="known_unit", column="unit_id", allowed_values={"012332", "012385"}),
    Regex(name="valid_plant_code", column="plant", regex=r"P\d{3}"),
)
```

```json title="One per-row result"
{"timestamp": 1645334535000, "temperature": 21.5, "unit_id": "012332", "plant": "P001",
 "valid_temperature": true, "known_unit": true, "valid_plant_code": true, ...}
```

## Available checks

All checks are imported from `streamdaq.checks`.

| Check | Parameters | `True` when |
|---|---|---|
| `InRange` | `name`, `column`, `low`, `high`, `inclusive_low=True`, `inclusive_high=False` | `low <= value < high` (bounds inclusive or exclusive as set) |
| `InSet` | `name`, `column`, `allowed_values` | the value is in `allowed_values` |
| `Regex` | `name`, `column`, `regex` | the value matches `regex`, starting at its beginning |
| `Length` | `name`, `column`, `must_be` | the value's length (as text) satisfies `must_be` |
| `Value` | `name`, `column`, `must_be`, `transformation=None` | the value, optionally transformed first, satisfies `must_be` |
| `InRowComparison` | `name`, `columns` (two column names), `operator` | `operator(first, second)` holds, with `operator` one of `"lt"`, `"le"`, `"eq"`, `"ne"`, `"gt"`, `"ge"` |

For how to write `must_be`, see [Assessments](assessments.md).

### Examples

```py
from streamdaq.checks import InRowComparison, Length, Value

# Product codes must be between 4 and 8 characters long
Length(name="valid_code_length", column="product_code", must_be="[4, 8]")

# Humidity in percent, given as a fraction in the data
Value(name="valid_humidity", column="humidity", must_be="[0, 100]", transformation=lambda h: h * 100)

# A reading's start must come before its end
InRowComparison(name="start_before_end", columns=["start", "end"], operator="lt")
```

!!! note "`Regex` matches from the start"
    `Regex` checks whether the pattern matches **at the beginning** of the value, like Python's `re.match`. To require the whole value to match, end the pattern with `$`, e.g. `r"P\d{3}$"`.

!!! warning "Check names and column names"
    Check results are added next to the input columns. A check with the same name as an input column replaces that column in the results, so give checks names that differ from your columns.
