import multiprocessing
from collections.abc import Callable
from typing import Any

import pathway as pw

from streamdaq.orchestration.utils import gracefully_kill
from streamdaq.schema.evb.definitions import _VALID_TIME_DIGITS


def _evb_native_schema_sniff_worker(
    queue: multiprocessing.Queue,
    get_table_function: Callable[[], pw.Table],
) -> None:  # pragma: no cover (runs in child process — coverage.py cannot track)
    """
    Child process running Pathway to sniff the first message's schema.
    """

    def on_change(key: pw.Pointer, row: dict, time: int, is_addition: bool):
        measurement: dict[str, Any] = row["measurements"][0].as_dict()
        fields: list[str] = measurement["fields"]
        values: list[Any] = measurement["values"][0]

        if not fields[0] == "time":
            return  # invalid fields, wait for the next message
        if (not isinstance(values[0], int)) or (not len(str(values[0])) == _VALID_TIME_DIGITS):
            return  # invalid values, wait for the next message
        if len(fields) != len(values):
            return  # invalid combination of fields and values, wait for the next message

        fields = fields[1:]
        values = values[1:]
        discovered_schema: tuple[tuple[str, type]] = tuple(
            [(field, type(value)) for field, value in zip(fields, values)]
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
) -> tuple[tuple[str, type]]:

    schema_queue = multiprocessing.Queue()
    sniffer_process = multiprocessing.Process(
        target=_evb_native_schema_sniff_worker, args=(schema_queue, get_table_function)
    )
    sniffer_process.start()

    try:
        discovered_schema = schema_queue.get(timeout=timeout_seconds)
    except multiprocessing.queues.Empty:
        raise TimeoutError(
            f"The EVB Schema Sniffer did not respond within {timeout_seconds} sec."
            "Make sure the EVB source is sending data and/or increase the timeout."
        )
    finally:
        gracefully_kill(sniffer_process, graceful_wait_seconds)

    return discovered_schema
