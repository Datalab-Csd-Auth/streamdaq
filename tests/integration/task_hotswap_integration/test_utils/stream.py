"""Deterministic two-batch input data for the task hot-swap integration test.

* Batch 1 asserts window [0, 1000); the trailing ``time=1100`` row closes it.
* Batch 2 asserts window [2000, 3000); the trailing ``time=3100`` row closes it.

Schema (simple, non-EVB):
    time   int   epoch-ms timestamp
    value  int   integer measurement
"""

import json
from pathlib import Path

TIME = "time"
INT = "value"

# Batch 1: fills window [0, 1000); the trailing 1100 row closes it.
FIRST_BATCH: list[dict[str, int]] = [
    {TIME: 100, INT: 5},
    {TIME: 300, INT: 5},
    {TIME: 1100, INT: 10},
]

# Batch 2: fills window [2000, 3000); the trailing 3100 row closes it.
SECOND_BATCH: list[dict[str, int]] = [
    {TIME: 2100, INT: 30},
    {TIME: 2300, INT: 40},
    {TIME: 3100, INT: 50},
]


def append_batch(input_path: Path, batch: list[dict[str, int]]) -> None:
    """Append a batch of rows as JSON lines to the file the streaming source is tailing."""
    with input_path.open("a") as input_file:
        for row in batch:
            input_file.write(json.dumps(row) + "\n")
