# Streamdaq {++v2++}

_Data quality monitoring for unbounded streams. **Made eas{~~y~>ier~~}.**_

### TL;DR

`streamdaq` allows you to monitor the quality of your data streams in just a few lines of Python code.
Before we dive into the details, here is a complete example. Easy, isn't it?


```py
# pip install streamdaq

from streamdaq import StreamDaQ, DaQMeasures as dqm, Windows

# Step 1: Configure your monitoring setup
daq = StreamDaQ().configure(
    window=Windows.tumbling(3),
    instance="user_id",
    time_column="timestamp",
    wait_for_late=1,
    time_format='%Y-%m-%d %H:%M:%S'
)

# Step 2: Define what Data Quality means for you
daq.check(dqm.count('interaction_events'), assess="(5, 15]", name="count") \
   .check(dqm.max('interaction_events'), assess=">5.09", name="max_interact") \

# Step 3: Start monitoring and let Stream DaQ do the work
daq.watch_out()
```

??? code-output "Output"
    ```
    Starting monitoring for task: default_task
    Task 'default_task': No source provided. Data set to artificial and format to native.
    Task 'default_task' started successfully
    All 1 tasks started successfully
                | user_id | window_start | window_end   | count       | max_interact
    ^JS0CHBP... | UserA   | 1775721771.0 | 1775721774.0 | (7, True)   | (10, True)
    ^JS00S9K... | UserA   | 1775721774.0 | 1775721777.0 | (20, False) | (10, True)
    ^JS0FH5B... | UserA   | 1775721777.0 | 1775721780.0 | (16, False) | (10, True)
    ^JS0C5TD... | UserA   | 1775721780.0 | 1775721783.0 | (16, False) | (10, True)
    ^Z94K0FQ... | UserB   | 1775721771.0 | 1775721774.0 | (7, True)   | (10, True)
    ^Z94NTD2... | UserB   | 1775721774.0 | 1775721777.0 | (10, True)  | (9, True)
    ^Z94VS27... | UserB   | 1775721777.0 | 1775721780.0 | (14, True)  | (9, True)
    ^Z94KVAB... | UserB   | 1775721780.0 | 1775721783.0 | (10, True)  | (10, True)
    ```
