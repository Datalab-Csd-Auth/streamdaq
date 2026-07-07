## 1. Python Best Practices Survey & Alignment

In alignment with the core issue requirement, we surveyed standard enterprise Python logging architectures (referencing industry frameworks, PEP standards, and community guidelines). StreamDaQ’s logging module adopts these best practices, mapping static logging structures to a dynamic streaming engine.

### Core Best Practices Adopted:

#### Avoid Root Logger Pollution
> **The Best Practice:** Libraries should never configure or log directly to the root logger (`logging.basicConfig()`), as this pollutes the global namespace of the application importing the library.

* **StreamDaQ Realization:** We employ a strictly namespaced logger hierarchy starting at `logging.getLogger("streamdaq")`. Submodules will inherit child namespaces (e.g., `streamdaq.validation`, `streamdaq.engine`), ensuring clean isolation, predictable propagation control (`logger.propagate = False`), and zero interference with the host application.

#### Adherence to Semantic Log Levels
> **The Best Practice:** Standardized execution levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) must be preserved semantically so that DevOps tools and engineers can accurately set alerting filters.

* **StreamDaQ Realization:**
    * `DEBUG`: Internal execution states, graph optimization, and data-flow routing.
    * `INFO`: Successful schema initializations, window tracking setups, and pipeline state changes.
    * `WARNING`: Non-breaking operational anomalies (e.g., late-arriving stream tuples arriving near the boundary).
    * `ERROR`: Critical configuration failures (e.g., malformed threshold rules during runtime reconfigurations) that block a query step but keep the background engine alive.

#### Standardized Formatting and Thread/Async Safety
> **The Best Practice:** Logs must contain unified metadata (timestamps, file names, line numbers) and be inherently thread-safe to handle concurrent processing.

* **StreamDaQ Realization:** Python’s built-in `logging.Handler` locks internal thread contexts natively during `emit()`. By structuring our custom output hooks strictly as extensions of the standard `logging.Handler` class, we leverage Python's thread-safe design. This ensures that concurrent data-stream evaluations do not block or cause race conditions during log routing.

#### The Separation of Concerns: Loggers vs. Handlers
> **The Best Practice:** Code should only be responsible for generating log records; configuring where those logs go (Console, Files, Sinks) is the operational responsibility of the user at the application entry point.

* **StreamDaQ Realization:** By default, StreamDaQ will attach a `logging.NullHandler()` to its parent namespace so it remains totally silent when imported. We expose a clear configuration macro (`configure_logging()`) to allow the user to choose exactly when, where, and how loud the logging outputs should be.

#### Transition to Structured Logging
> **The Best Practice:** Modern logging ecosystems move away from unstructured text strings in favor of structured key-value formats (like JSON) to make searching and ingestion into external tools trivial.

* **StreamDaQ Realization:** Because our specification translates logs directly into a "Logs-as-a-Stream" table model, structured logs are a natural byproduct. Log attributes (timestamp, level, message, traceback) are mapped straight into explicit columns in a relational schema, fulfilling the highest standard of modern structured logging.

## 2. StreamDaQ Centralized Logging Module
### High-Level Technical Specification

* This document outlines the design for a centralized, stream-native logging infrastructure for StreamDaQ.
* The architecture balances:
    * Traditional application logging (for validation, setup, and diagnostics), with
    * Stream-first features, turning error states and operational events into queryable data streams.

### Architectural Goals & Core Pillars
The logging module is built around three operational requirements:
1. **Complete runtime abstraction over internal Pathway engine logs**, allowing users to toggle or filter background streaming logs without losing StreamDaQ diagnostic telemetry.
2. **Unified reporting for runtime data quality checks**, structural validation (e.g., windows and schemas), as well as on-the-fly threshold reconfigurations.
3. **A dual-layered model** where high-severity logs (e.g., configuration failures or corrupted metrics) bypass standard system boundaries and emit directly into custom streaming output hooks (e.g., Kafka, PostgreSQL, etc.).

### Structural Design & Layout
To prevent friction across branches as development continues, the logging system operates as a standalone package inside the source tree:
```text
src/streamdaq/logging/
├── __init__.py
├── handlers.py          # Custom stream handlers (e.g., Custom JSON/Output Hooks)
├── managers.py          # State engine for isolating Pathway vs StreamDaQ log levels
└── stream.py            # Converts standard log buffers into reactive Pathway Tables
```
## 3. Detailed Specifications

### Third-Party Isolation & Engine Controls
Pathway runs intensive, low-level Rust and C++ streaming execution processes. To prevent this telemetry from saturating the terminal, StreamDaQ wraps the global logger configuration state.

* **Mechanism:** Intercepts named log entries under the `pathway` namespace, mapping execution levels independently from the root `streamdaq` configuration context.

```python
import logging
from typing import Optional, Union

def configure_logging(
    level: Union[int, str] = logging.INFO,
    pathway_level: Optional[Union[int, str]] = logging.WARNING,
    enable_console: bool = True
) -> None:
    """
    Bootstrap entry point for StreamDaQ logging isolation.
    Enforces independent granularity between StreamDaQ and the underlying engine.
    """
    # Configure StreamDaQ Base Logging
    sd_logger = logging.getLogger("streamdaq")
    sd_logger.setLevel(level)

    # Isolate or mute Pathway execution logs
    pw_logger = logging.getLogger("pathway")
    if pathway_level is None:
        pw_logger.addHandler(logging.NullHandler())
        pw_logger.propagate = False
    else:
        pw_logger.setLevel(pathway_level)

    if enable_console and not sd_logger.handlers:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
        )
        console_handler.setFormatter(formatter)
        sd_logger.addHandler(console_handler)
```
As StreamDaQ evolves toward dynamic execution graphs (such as updating threshold configuration metrics on the fly), tracking configuration validation failures is critical.

* **Mechanism:** A centralized diagnostic decorator pattern to ensure validation issues across windows, checks, and calculations are uniformly formatted and isolated before hitting the streaming runtime.

```python
import functools

logger = logging.getLogger("streamdaq.validation")

def validate_config(component_type: str):
    """
    Decorator for intercepting validation exceptions and converting them
    into clean, structured system alert payloads.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (ValueError, TypeError, KeyError) as e:
                logger.error(
                    f"Invalid configuration encountered during {component_type} init. "
                    f"Details: {str(e)}",
                    extra={"component": component_type, "phase": "initialization"}
                )
                raise e
        return wrapper
    return decorator
```
### Logs-as-a-Stream & Extensible Output Hooks
To process log payloads directly within a streaming pipeline, log generation can be converted into an ongoing streaming table. High-priority log events (like a `logging.ERROR` resulting from an invalid runtime threshold configuration change) can automatically write directly to external sinks via background handler extensions.

```python
import logging
from typing import Callable, Any

class StreamOutputHookHandler(logging.Handler):
    """
    Intercepts specific threshold logs and routes them to user-defined
    sinks or storage tables.
    """
    def __init__(self, target_hook: Callable[[str, dict], None], level: int = logging.ERROR):
        super().__init__(level=level)
        self.target_hook = target_hook

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {
                "timestamp": record.created,
                "level": record.levelname,
                "module": record.module,
                "line": record.lineno,
                "message": record.getMessage(),
                "traceback": self.format(record) if record.exc_info else None
            }
            # Execute hook connection (e.g., route payload directly to Postgres or Kafka)
            self.target_hook(record.name, payload)
        except Exception:
            self.handleError(record)
```
## 4. User-Facing Implementation Blueprint

When implemented, a data engineer using StreamDaQ can:
* Toggle system verbosity
* Configure alerts
* Write records to terminal outputs and data lakes simultaneously

This can be achieved using the following interface pattern:

```python
import pathway as pw
from streamdaq.logging import configure_logging, StreamOutputHookHandler
from streamdaq.window import WindowConfig

# 1. Turn down Pathway verbosity, preserve StreamDaQ diagnostics
configure_logging(level="INFO", pathway_level="WARNING")

# 2. Optionally append an output hook to route critical errors to a data sink
def my_postgres_sink_hook(logger_name: str, log_data: dict):
    # e.g., PostgresClient.write_runtime_error(...)
    pass

import logging
logging.getLogger("streamdaq").addHandler(
    StreamOutputHookHandler(target_hook=my_postgres_sink_hook, level=logging.ERROR)
)

# 3. Validation alerts handle corrupted setups clean before runtime
# If duration_seconds is malformed, logging captures it seamlessly
window = WindowConfig.tumbling(
    duration_seconds="invalid_string",
    time_column="timestamp"
)
```
