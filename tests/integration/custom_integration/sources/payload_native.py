"""Builds the ``bulk_create`` payload for the custom-source integration suite."""

SOURCE_TYPE = "FiniteCustomPythonSource"
MEASURE_TYPE = "MaxDropBetweenOkReadings"


def build_native_request_payload(output_filename: str) -> list[dict]:
    """Single tumbling-window task fed by the custom source."""
    return [
        {
            "name": "custom_source_tumbling",
            "windowby_column": "time",
            "input": {"type": SOURCE_TYPE, "params": {"connector_params": {}}},
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
