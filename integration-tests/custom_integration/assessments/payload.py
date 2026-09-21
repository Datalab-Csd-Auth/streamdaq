"""Builds the ``bulk_create`` payload for the custom-assessment integration suite."""

from custom_integration.stream import MEASUREMENT, STATUS, TIME

_MODULE = "custom_integration.stream"
_CLASS = "FiniteCustomStream"
MEASURE_TYPE = "MaxDropBetweenOkReadings"
ASSESSMENT_NAME = "IsDropSpike"


def build_request_payload(output_filename: str) -> list[dict]:
    """Single tumbling-window task whose check resolves must_be via a custom assessment."""
    return [
        {
            "name": "assessment_tumbling",
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
                        "name": "wc_drop_spike",
                        "measure": {"type": MEASURE_TYPE},
                        "must_be": ASSESSMENT_NAME,
                    }
                ],
            },
        }
    ]
