"""A finite, deterministic compact (EVB) input stream for the custom_integration suite.

Each row is a raw EVB message whose native form has a ``time``, a ``measurement`` field and a
``status`` tag, reproducing the same two-window scenario as :mod:`custom_integration.stream` (so
the ``MaxDropBetweenOkReadings`` measure yields the same per-window result). EVB requires 13-digit
epoch-ms timestamps, so the small offsets of the native stream are shifted onto a 13-digit base.
Rows are emitted out of time order within each window to exercise ``sort_by_column="time"``.
"""

import pathway as pw

_TIME_BASE = 1_700_000_000_000

# (time_offset, measurement, status); windows are [base, base+1000) and [base+1000, base+2000).
ROWS: list[tuple[int, float, str]] = [
    # Window 1: time-sorted OK [10.0, 2.0, 9.0] -> max drop 8.0 (>= 2) -> TRUE.
    (500, 2.0, "OK"),
    (100, 10.0, "OK"),
    (700, 9.0, "OK"),
    (300, 3.0, "WARN"),
    # Window 2: time-sorted OK [3.5, 4.0, 8.0] -> max drop -0.5 (< 2) -> FALSE.
    (1700, 8.0, "OK"),
    (1300, 4.0, "OK"),
    (1500, 5.0, "WARN"),
    (1100, 3.5, "OK"),
]


class FiniteCompactEVBStream(pw.io.python.ConnectorSubject):
    def run(self) -> None:
        for time_offset, measurement, status in ROWS:
            message = {
                "name": "Reading",
                "tags": {"status": status},
                "type": "Points",
                "fields": ["time", "measurement"],
                "values": [[_TIME_BASE + time_offset, measurement]],
            }
            self.next(measurements=[message])
