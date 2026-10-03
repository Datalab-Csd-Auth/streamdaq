<p align="center">
  <img height="400px" src="https://github.com/user-attachments/assets/a42a440d-d61c-4cf8-aff0-092209aea052" alt="Stream DaQ logo">
</p>

<p align="center">
  <a href="https://pypi.org/project/streamdaq/"><img src="https://img.shields.io/pypi/v/streamdaq?label=release&color=blue&" alt="PyPI version"></a>
  <a href="https://pypi.org/project/streamdaq/"><img src="https://img.shields.io/pypi/pyversions/streamdaq?color=purple" alt="Python versions"></a>
  <a href="https://pepy.tech/project/streamdaq"><img src="https://pepy.tech/badge/streamdaq" alt="Downloads"></a>
  <a href="https://datalab-csd-auth.github.io/streamdaq/"><img src="https://img.shields.io/website?label=docs&url=https%3A%2F%2Fdatalab-csd-auth.github.io/streamdaq%2F" alt="Documentation"></a>
  <a href="https://opensource.org/license/apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-yellow.svg" alt="License: Apache 2.0"></a>
  <a href="https://arxiv.org/abs/2506.06147"><img src="https://img.shields.io/badge/arXiv-2506.06147-b31b1b.svg" alt="License: Apache 2.0"></a>
</p>


**Streamdaq V2**: _Data quality monitoring for unbounded streams. Made easier._

### Installation
```bash
pip install streamdaq
```

You can verify installation with `pip install streamdaq`.

To download a specific version of Streamdaq use `pip install --update streamdaq==<your_desired_version>`.

### TL;DR

`streamdaq` allows you to monitor the quality of your data streams in just a few lines of Python code.
Before we dive into the details, here is a complete example.

```py
from streamdaq.checks import InRange, WindowDataQualityCheck
from streamdaq.measures import Count, DistinctCount, MostFrequent
from streamdaq.sessions import Session
from streamdaq.tasks import Task
import pathway as pw


def is_seven_frequent(most_frequent: tuple) -> bool:
    return 7 in most_frequent


# Step 2: Create a monitoring task that reads the stream and prints the results
task = Task(
    name="interactions",
    input=read_stream,
    output=output_sink,
    windowby_column="timestamp",
    include_window_bounds=True,
)

# Step 3: Define what Data Quality means for you
# Per-row checks, evaluated on every incoming element
task.add_instant_checks(
    InRange(name="valid_events", column="interaction_events", low=0, high=10),
)
# Per-window checks, evaluated on every tumbling window of 10 time units
task.add_window_checks(
    WindowDataQualityCheck("interaction_count", Count("interaction_events"), "(5, 15]"),
    WindowDataQualityCheck("lucky_sevens", MostFrequent("interaction_events"), is_seven_frequent),
    WindowDataQualityCheck("interaction_distinct", DistinctCount("interaction_events"), "<= 5"),
    window=pw.temporal.tumbling(duration=10),
)

# Step 4: Kick-off monitoring and let Stream DaQ do the work while you focus on the important
Session(tasks=[task]).start()
```


Output

```bash
# Instant Checks Output
user_id | timestamp | interaction_events | valid_events
 UserA  |     2     |         3          |    True
 UserB  |     3     |         7          |    True
 UserA  |     1     |         7          |    True
 UserB  |    12     |         4          |    True
 UserA  |     4     |        12          |    False
 UserB  |     8     |         7          |    True
 UserB  |     5     |         5          |    True
 UserA  |    11     |         2          |    True
 UserA  |    13     |         4          |    True
 UserB  |     6     |         7          |    True
 UserA  |     7     |         9          |    True
 UserB  |    14     |         1          |    True

# Window Checks Output
window_start | window_end | interaction_count | lucky_sevens | interaction_distinct
      0      |     10     |       True        |    True      |        True
     10      |     20     |       False       |    False     |        True
```

## Motivation
Remember the joy of bath time with those trusty rubber ducks, keeping us company while floating through the bubbles?
Well, think of **Stream DaQ** as the duck for your data — keeping your streaming data clean and afloat in a sea of
information. Just like those bath ducks helped make our playtime fun and carefree, Stream DaQ keeps an eye on your data
and lets you know the moment things get messy, so you can take action ***in real time***!


## Stream DaQ's architecture

![StreamDaQ architecture animation](https://github.com/user-attachments/assets/d57377c9-d0fc-4a8e-8346-d01204da09a2)


## Acknowledgements

Special thanks to [Maria Kavouridou](https://www.linkedin.com/in/maria-kavouridou/) for putting effort and love, in
order to give birth to the Stream DaQ logo.
