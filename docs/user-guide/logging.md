# :scroll: Logging

Stream DaQ logs through Python's standard `logging` module, under the `streamdaq` logger. When you import Stream DaQ, it sets up logging with these defaults:

- Stream DaQ's own messages at `INFO` level and above, printed to the terminal;
- Pathway's messages at `WARNING` level and above;
- Stream DaQ's messages are kept separate from your application's own logging.

## Changing the setup

Call `configure_logging` to change it:

```py
import logging

from streamdaq.logging import configure_logging

configure_logging(level=logging.WARNING, pathway_level=None)
```

| Setting | Default | Meaning |
|---|---|---|
| `level` | `logging.INFO` | Minimum level for Stream DaQ's messages. |
| `pathway_level` | `logging.WARNING` | Minimum level for Pathway's messages. `None` silences them. |
| `enable_console` | `True` | Print Stream DaQ's messages to the terminal. |
| `log_format` | `"[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"` | Format of each line. |
| `date_format` | `"%Y-%m-%dT%H:%M:%S"` | Format of the time in each line. |

## Sending logs elsewhere

Add handlers to the `streamdaq` logger, e.g. to write to a file instead of the terminal:

```py
import logging

from streamdaq.logging import JsonFormatter, configure_logging

configure_logging(enable_console=False)

handler = logging.FileHandler("streamdaq.log")
handler.setFormatter(JsonFormatter())  # one JSON object per line
logging.getLogger("streamdaq").addHandler(handler)
```

For other destinations, implement a `LogHook` (with `emit`, `flush` and `close`) and attach it with `LogHookHandler(hook)`.
