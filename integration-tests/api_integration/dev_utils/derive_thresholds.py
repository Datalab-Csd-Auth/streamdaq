"""Dev-time helper to compute each measure's per-window values over the fixed stream.

Run it (``uv run -m api_integration.dev_utils.derive_thresholds`` from ``integration-tests/``)
whenever ``stream.py`` changes, to see each measure's per-window results and pick a
``must_be`` threshold that sits between the min and max (so at least one window passes and
at least one fails). This is a development aid, not part of the test suite.
"""

import pandas as pd
import pathway as pw
from api_integration.test_utils.registry import MEASURE_SPECS
from api_integration.test_utils.stream import COLUMNS, ROWS

from streamdaq.checks.window.base import WindowDataQualityCheck
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.measures.registry import MEASURE_REGISTRY


def per_window_values(measure: DataQualityMeasure, window) -> list:
    """Return the measure's value for each window over the fixed stream."""
    table = pw.debug.table_from_pandas(pd.DataFrame(ROWS, columns=COLUMNS))
    check = WindowDataQualityCheck("c", measure, must_be=None)
    reduced = table.windowby(
        table.time, window=window, behavior=pw.temporal.exactly_once_behavior()
    ).reduce(**check.get_reduce_kwargs())

    expression = check.get_measurement_expression()
    if expression is not None:
        result = reduced.with_columns(c=expression).select(pw.this.c)
    else:
        result = reduced.select(c=pw.this.c)
    return pw.debug.table_to_pandas(result)["c"].tolist()


def main() -> None:
    window = pw.temporal.sliding(duration=1000, hop=500)
    for name, spec in sorted(MEASURE_SPECS.items()):
        try:
            values = per_window_values(MEASURE_REGISTRY[name](**spec.params), window)
            distinct = len(set(map(str, values)))
            flag = "" if distinct >= 2 else "  <-- SAME across windows: cannot discriminate"
            print(f"{name}: {values}{flag}")
        except Exception as e:
            print(f"{name}: ERROR {e}")


if __name__ == "__main__":
    main()
