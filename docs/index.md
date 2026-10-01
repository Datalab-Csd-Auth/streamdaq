# Streamdaq {++v2++}

_Data quality monitoring for unbounded streams. **Made eas{~~y~>ier~~}.**_

### Installation
```bash
pip install streamdaq
```

!!! annotate note
    You can verify installation with `#!bash pip show streamdaq`. You can download a specific
    version with `#!bash pip install --update streamdaq==<your_desired_version>`.


### TL;DR

`streamdaq` allows you to monitor the quality of your data streams in just a few lines of Python code.
Before we dive into the details, here is a complete example. Easy, isn't it?  (1)
{ .annotate }

1.  :man_raising_hand: This is an example annotation in **plain text**.


```py { .annotate }
# pip install streamdaq
import pathway as pw

from streamdaq.checks import InRange, WindowDataQualityCheck
from streamdaq.measures import Count, DistinctCount, MostFrequent
from streamdaq.sessions import Session
from streamdaq.tasks import Task


def is_seven_frequent(most_frequent: tuple) -> bool:
    return 7 in most_frequent


# Step 2: Create a monitoring task that reads the stream and prints the results
task = Task(
    name="interactions",
    input=read_stream,  # (2)!
    output=output_sink, # (1)!
    windowby_column="timestamp",
    include_window_bounds=True,  # (3)!
)

# Step 3: Define what Data Quality means for you
# Per-row checks, evaluated on every incoming element
task.add_instant_checks(
    InRange(name="valid_events", column="interaction_events", low=0, high=10),
)
# Per-window checks, evaluated on every tumbling window of 10 time units
task.add_window_checks(
    WindowDataQualityCheck("interaction_count", Count("interaction_events"), "(5, 15]"),
    WindowDataQualityCheck("my_freq", MostFrequent("interaction_events"), is_seven_frequent),
    WindowDataQualityCheck("interaction_distinct", DistinctCount("interaction_events"), "<= 5"),
    window=pw.temporal.tumbling(duration=10),
)

# Step 4: Kick-off monitoring and let Stream DaQ do the work while you focus on the important
Session(tasks=[task]).start()
```

1.  `output` accepts any function that takes a table. Here, every result row is printed as it arrives. Built-in sinks
    write to CSV, JSON Lines, Kafka, MQTT or Postgres instead.
2.  Any function that returns a Pathway table can be the input, for example one reading from Kafka, MQTT or a CSV file.
3.  Adds `window_start` and `window_end` as the first columns of every per-window result.
4.  Any output sink that emits a pw.Table

??? code-output "Output"
    ```
    {'user_id': 'UserA', 'timestamp': 2, 'interaction_events': 3, 'valid_events': True}
    {'user_id': 'UserB', 'timestamp': 3, 'interaction_events': 7, 'valid_events': True}
    {'user_id': 'UserA', 'timestamp': 1, 'interaction_events': 7, 'valid_events': True}
    {'user_id': 'UserB', 'timestamp': 12, 'interaction_events': 4, 'valid_events': True}
    {'user_id': 'UserA', 'timestamp': 4, 'interaction_events': 12, 'valid_events': False}
    {'user_id': 'UserB', 'timestamp': 8, 'interaction_events': 7, 'valid_events': True}
    {'user_id': 'UserB', 'timestamp': 5, 'interaction_events': 5, 'valid_events': True}
    {'user_id': 'UserA', 'timestamp': 11, 'interaction_events': 2, 'valid_events': True}
    {'user_id': 'UserA', 'timestamp': 13, 'interaction_events': 4, 'valid_events': True}
    {'user_id': 'UserB', 'timestamp': 6, 'interaction_events': 7, 'valid_events': True}
    {'user_id': 'UserA', 'timestamp': 7, 'interaction_events': 9, 'valid_events': True}
    {'user_id': 'UserB', 'timestamp': 14, 'interaction_events': 1, 'valid_events': True}
    {'window_start': 0, 'window_end': 10, 'interaction_count': True, 'my_freq': True, 'interaction_distinct': True}
    {'window_start': 10, 'window_end': 20, 'interaction_count': False, 'my_freq': False, 'interaction_distinct': True}
    ```
