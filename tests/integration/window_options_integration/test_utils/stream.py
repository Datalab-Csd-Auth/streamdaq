"""Deterministic five-batch input data for the Pathway-delegated window options test.

Schema (native):
    time      int   epoch-ms timestamp
    value     int   integer measurement
    instance  str   instance key used as ``groupby_column``
"""

import json
from pathlib import Path

TIME = "time"
INT = "value"
INSTANCE = "instance"

# Batch 1: seeds windows [0, 1000), [1000, 2000) and [2000, 3000); nothing closes yet.
FIRST_BATCH: list[dict[str, int | str]] = [
    {TIME: 100, INT: 1, INSTANCE: "a"},
    {TIME: 200, INT: 2, INSTANCE: "b"},
    {TIME: 300, INT: 3, INSTANCE: "b"},
    {TIME: 1100, INT: 4, INSTANCE: "a"},
    {TIME: 1200, INT: 5, INSTANCE: "a"},
    {TIME: 1300, INT: 6, INSTANCE: "b"},
    {TIME: 2100, INT: 7, INSTANCE: "a"},
    {TIME: 2200, INT: 8, INSTANCE: "b"},
    {TIME: 2300, INT: 9, INSTANCE: "b"},
]

# Batch 2: the 3600 row closes [0, 1000) and moves the watermark past 3000.
SECOND_BATCH: list[dict[str, int | str]] = [
    {TIME: 3600, INT: 10, INSTANCE: "a"},
]

# Batch 3: late row for [2000, 3000) within the wait frame (kept); the 4600 row closes [1000, 2000).
THIRD_BATCH: list[dict[str, int | str]] = [
    {TIME: 2500, INT: 11, INSTANCE: "b"},
    {TIME: 4600, INT: 12, INSTANCE: "b"},
]

# Batch 4: the 5600 row closes [2000, 3000).
FOURTH_BATCH: list[dict[str, int | str]] = [
    {TIME: 5600, INT: 13, INSTANCE: "a"},
]

# Batch 5: late row for [2000, 3000) beyond the wait frame (dropped); 6600 closes [3000, 4000).
FIFTH_BATCH: list[dict[str, int | str]] = [
    {TIME: 2700, INT: 14, INSTANCE: "a"},
    {TIME: 6600, INT: 15, INSTANCE: "b"},
]

# Each batch paired with the total number of window rows expected once it is processed.
BATCHES_WITH_EXPECTED_WINDOW_ROWS: list[tuple[list[dict[str, int | str]], int]] = [
    (FIRST_BATCH, 0),
    (SECOND_BATCH, 2),
    (THIRD_BATCH, 4),
    (FOURTH_BATCH, 6),
    (FIFTH_BATCH, 7),
]


def append_batch(input_path: Path, batch: list[dict[str, int | str]]) -> None:
    """Append a batch of rows as JSON lines to the file the streaming source is tailing."""
    with input_path.open("a") as input_file:
        for row in batch:
            input_file.write(json.dumps(row) + "\n")
