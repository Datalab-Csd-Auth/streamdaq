"""A finite, fully deterministic StreamDAQ input stream for integration testing.

The stream emits a small, fixed set of rows and then returns,making the end-to-end result
reproducible for exact assertions.

Schema (simple, non-EVB):
    time        int    epoch-ms timestamp
    value       int    integer measurement
    measurement float  floating-point measurement
    note        str    free-text string
    status      str    categorical string from a small fixed vocabulary
"""

import pathway as pw

ROWS: list[tuple[int, int, float, str, str]] = [
    # Window 1 [0,1000)
    (100, 5, 1.5, "aa", "OK"),
    (300, 5, 2.5, "bb", "OK"),
    # Window 2 [1000,2000)
    (1100, 10, 3.125, "hello world", "WARN"),
    (1300, 20, 4.75, "123", "ERROR"),
    (1500, 60, 12.5, "", "OK"),
    (1700, 95, 14.0, "45678", "WARN"),
    # Window 3 [2000,3000)
    (2100, -1, 5.0, "note", "OK"),
    (2300, 15, 6.5, "abcdef", "ERROR"),
    (2500, 15, 6.5, "999", "OK"),
    (2700, 22, 7.125, "42", "WARN"),
    # Window 4 [3000,4000)
    (3100, 200, 20.0, "abcdefghij", "OK"),
    (3300, 120, 15.5, "x", "ERROR"),
    (3500, 40, 8.0, "1234567", "ERROR"),
    (3700, 5, 0.5, "z", "ERROR"),
]

TIME = "time"
INT = "value"
FLOAT = "measurement"
TEXT = "note"
CATEGORICAL = "status"

COLUMNS = (TIME, INT, FLOAT, TEXT, CATEGORICAL)


class IntegrationInputSchema(pw.Schema):
    time: int
    value: int
    measurement: float
    note: str
    status: str


class FiniteIntegrationStream(pw.io.python.ConnectorSubject):
    def run(self) -> None:
        for row in ROWS:
            self.next(**dict(zip(COLUMNS, row)))
