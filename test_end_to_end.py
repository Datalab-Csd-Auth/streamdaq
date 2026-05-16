import pathway as pw

from streamdaq.checks import InRange, WindowDataQualityCheck
from streamdaq.measures import InRangeCount, Mean
from streamdaq.sessions.base import Session
from streamdaq.tasks.base import Task


def get_table():
    return pw.debug.table_from_markdown(
        """
  times | instance |  t |  v
    1   | 0        |  1 |  10
    2   | 0        |  2 |  1
    3   | 0        |  4 |  3
    4   | 0        |  8 |  2
    5   | 0        |  9 |  4
    6   | 0        |  10|  8
    7   | 1        |  1 |  9
    8   | 1        |  2 |  16
  """
    )


in_range_check = InRange(
    name="valid_value",
    column="v",
    low=3,
    high=10,
    inclusive_low=True,
    inclusive_high=True,
)

task: Task = (
    Task(
        input=get_table,
        output=pw.io.jsonlines.write,
        output_kwargs={"filename": "papari.jsonl"},
        windowby_column="times",
    )
    .add_instant_checks(in_range_check)
    .add_window_checks(
        WindowDataQualityCheck(
            "mean_value_is_valid",
            Mean(column="v", precision=3),
            must_be="[1, 4]",
        ),
        WindowDataQualityCheck(
            "at_least_2_vs_in_3_10",
            InRangeCount(column="v", low=3, high=10, inclusive_high=True),
            must_be=">=2",
        ),
        window=pw.temporal.sliding(hop=1, duration=3, origin=0),
    )
)

session: Session = Session(tasks=[task], name="test_session")

session.start()
