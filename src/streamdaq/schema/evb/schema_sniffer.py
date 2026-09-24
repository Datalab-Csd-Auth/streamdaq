import multiprocessing
from collections.abc import Callable
from queue import Empty as EmptyQueueException
from typing import Any

import dill
import pathway as pw
from pydantic import ValidationError

from streamdaq.orchestration.utils import gracefully_kill, load_additional_files
from streamdaq.schema.evb.definitions import (
    EVBKeyNames,
    SniffedEVBSchema,
    ValidatableEVBSchema,
    _EVBMeasurement,
)
from streamdaq.schema.evb.wrangling import Transform


def _evb_native_schema_sniff_worker(
    queue: multiprocessing.Queue,
    get_table_function_payload: bytes,
    files_path: str | None = None,
) -> None:  # pragma: no cover (runs in child process — coverage.py cannot track)
    """
    Child process running Pathway to sniff the first message's schema.
    """
    if files_path:
        load_additional_files(files_path)

    get_table_function = dill.loads(get_table_function_payload)

    def on_change(key: pw.Pointer, row: dict, time: int, is_addition: bool) -> None:
        try:
            evb = ValidatableEVBSchema(
                **Transform.to_pydantic_validatable(row[EVBKeyNames.MEASUREMENTS]),
                strict=True,
            )
        except ValidationError:
            # Invalid message, wait for the next one
            return

        measurement: _EVBMeasurement = evb.measurements[0]
        fields: list[str] = measurement.fields[1:]
        values: list[Any] = measurement.values[0][1:]
        tags: dict[str, str] = measurement.tags

        discovered_schema: SniffedEVBSchema = SniffedEVBSchema(
            fields=fields, values=values, tags=tags
        )
        queue.put(discovered_schema.serialize())

    table = get_table_function()
    pw.io.subscribe(table, on_change)
    pw.run(monitoring_level=pw.MonitoringLevel.NONE, default_logging=False)


def discover_native_evb_schema(
    *,
    get_table_function: Callable[[], pw.Table],
    timeout_seconds: int = 10,
    graceful_wait_seconds: int = 3,
    files_path: str | None = None,
) -> tuple[tuple[str, type]]:

    schema_queue = multiprocessing.Queue()
    get_table_function_payload = dill.dumps(get_table_function)
    sniffer_process = multiprocessing.Process(
        target=_evb_native_schema_sniff_worker,
        args=(schema_queue, get_table_function_payload, files_path),
    )
    sniffer_process.start()

    try:
        discovered_schema = schema_queue.get(timeout=timeout_seconds)
    except EmptyQueueException:
        raise TimeoutError(
            f"The EVB Schema Sniffer did not respond within {timeout_seconds=}. "
            "Make sure the EVB source is sending data and/or increase the timeout."
        )
    finally:
        gracefully_kill(sniffer_process, graceful_wait_seconds)

    return discovered_schema
