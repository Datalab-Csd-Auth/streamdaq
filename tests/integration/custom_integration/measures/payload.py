"""Builds the ``bulk_create`` payload for the custom-measure integration suite."""

from custom_integration.stream_native import MEASUREMENT, STATUS, TIME

_MODULE = "custom_integration.stream_native"
_CLASS = "FiniteCustomStream"
MEASURE_TYPE = "MaxDropBetweenOkReadings"


def build_request_payload(output_filename: str) -> list[dict]:
    """Single tumbling-window task exercising the custom measure."""
    return [
        {
            "name": "custom_tumbling",
            "windowby_column": TIME,
            "input": {
                "type": "python_connector",
                "params": {
                    "module": _MODULE,
                    "class_name": _CLASS,
                    "data_type": "native",
                    "schema": {
                        TIME: "int",
                        MEASUREMENT: "float",
                        STATUS: "str",
                    },
                },
            },
            "output": {"type": "jsonlines", "params": {"filename": output_filename}},
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
