"""A finite, deterministic StreamDAQ input stream shared by the custom_integration suites.

Rows are emitted intentionally out of time order within each tumbling window so the pipeline
must sort them, verifying the custom measure's ``sort_by_column="time"``.

Schema:
    time        int    epoch-ms timestamp
    measurement float  floating-point measurement
    status      str    categorical string (OK/WARN)
"""

import pathway as pw

TIME = "time"
MEASUREMENT = "measurement"
STATUS = "status"

COLUMNS = (TIME, MEASUREMENT, STATUS)

ROWS: list[tuple[int, float, str]] = [
    # Window 1 [0,1000): time-sorted OK [10.0, 2.0, 9.0] -> max drop 8.0 (>= 2) -> TRUE.
    # Emission order OK [2.0, 10.0, 9.0] -> max drop 1.0 (< 2) -> FALSE, so a missing sort flips it.
    (500, 2.0, "OK"),
    (100, 10.0, "OK"),
    (700, 9.0, "OK"),
    (300, 3.0, "WARN"),
    # Window 2 [1000,2000): time-sorted OK [3.5, 4.0, 8.0] -> max drop -0.5 (< 2) -> FALSE.
    # Emission order OK [8.0, 4.0, 3.5] -> max drop 4.0 (>= 2) -> TRUE, so a missing sort flips it.
    (1700, 8.0, "OK"),
    (1300, 4.0, "OK"),
    (1500, 5.0, "WARN"),
    (1100, 3.5, "OK"),
]


class FiniteCustomStream(pw.io.python.ConnectorSubject):
    def run(self) -> None:
        for row in ROWS:
            self.next(**dict(zip(COLUMNS, row)))
