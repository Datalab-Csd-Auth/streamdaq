"""Builds the ``bulk_create`` payload for the custom-sink integration suite."""

from custom_integration.stream_native import MEASUREMENT, STATUS, TIME

_MODULE = "custom_integration.stream_native"
_CLASS = "FiniteCustomStream"
MEASURE_TYPE = "MaxDropBetweenOkReadings"
SINK_TYPE = "JsonlinesFileSink"


def build_request_payload(output_filename: str) -> list[dict]:
    """Single tumbling-window task whose results are written by the custom sink."""
    return [
        {
            "name": "custom_sink_tumbling",
            "windowby_column": TIME,
            "input": {
                "type": "python_connector",
                "params": {
                    "module": _MODULE,
                    "class_name": _CLASS,
                    "data_type": "native",
                    "schema": {TIME: "int", MEASUREMENT: "float", STATUS: "str"},
                },
            },
            "output": {"type": SINK_TYPE, "params": {"filename": output_filename}},
            "window_checks_config": {
                "window": {"type": "tumbling", "params": {"duration": 1000}},
                "checks": [
                    {
                        "name": "wc_max_drop",
                        "measure": {"type": MEASURE_TYPE},
                        "must_be": ">= 2",
                    }
                ],
            },
        }
    ]
