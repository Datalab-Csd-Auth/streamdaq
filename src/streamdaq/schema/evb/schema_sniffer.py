import multiprocessing
from queue import Empty as EmptyQueueException

from collections.abc import Callable
from typing import Any, Literal, Optional

import pathway as pw
from pydantic import ValidationError

from streamdaq.orchestration.utils import gracefully_kill
from streamdaq.schema.evb.definitions import EVBKeyNames, ValidatableEVBSchema
from streamdaq.schema.evb.wrangling import Transform, TNATIVE_EVB_SCHEMA


def _evb_native_schema_sniff_worker(
    queue: multiprocessing.Queue,
    get_table_function: Callable[[], pw.Table],
) -> None:  # pragma: no cover (runs in child process — coverage.py cannot track)
    """
    Child process running Pathway to sniff the first message's schema.
    """

    def on_change(
        key: pw.Pointer,
        row: dict[str, tuple[pw.Json, ...]],
        time: int,
        is_addition: bool
    ) -> None:
        try:
            evb = ValidatableEVBSchema.model_validate(
                Transform.to_pydantic_validatable(row[EVBKeyNames.MEASUREMENTS]),
                strict=True
            )
        except ValidationError as ve:
            raise ValidationError(row)

        if len(evb.measurements) == 0 or \
            len(evb.measurements[0].values) == 0 or \
            len(evb.measurements[0].values[0]) == 0:
            return # empty EVB

        measurement = evb.measurements[0]

        fields = measurement.fields[1:]
        first_values = measurement.values[0][1:]
        tags = measurement.tags
        
        discovered_schema: TNATIVE_EVB_SCHEMA = {
            "fields": tuple(
                (field, type(value))
                for field, value in zip(fields, first_values)
            ),
            "tags": tuple()
        }

        if len(tags) > 0:
            discovered_schema["tags"] = tuple(
                (tagname, str)
                for tagname in Transform.to_encoded_tags(tags).keys()
            )
        queue.put(discovered_schema)

    table = get_table_function()
    pw.io.subscribe(table, on_change)
    pw.run(monitoring_level=pw.MonitoringLevel.NONE)


def discover_native_evb_schema(
    *,
    get_table_function: Callable[[], pw.Table],
    timeout_seconds: int = 10,
    graceful_wait_seconds: int = 3,
) -> TNATIVE_EVB_SCHEMA:
    """
    Spawns a PW Schema sniffer in a child process to deduce the native schema
    from a compact EVB schema.
    """

    schema_queue = multiprocessing.Queue()
    sniffer_process = multiprocessing.Process(
        target=_evb_native_schema_sniff_worker, args=(schema_queue, get_table_function)
    )
    sniffer_process.start()

    try:
        discovered_schema = schema_queue.get(timeout=timeout_seconds)
    except EmptyQueueException:
        raise TimeoutError(
            f"The EVB Schema Sniffer did not respond within {timeout_seconds} sec."
            "Make sure the EVB source is sending data and/or increase the timeout."
        )
    finally:
        gracefully_kill(sniffer_process, graceful_wait_seconds)

    return discovered_schema
