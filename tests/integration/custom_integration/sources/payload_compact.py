"""Builds the ``bulk_create`` payload for the compact custom-source integration suite."""

SOURCE_TYPE = "FiniteCompactEVBSource"
MEASURE_TYPE = "MaxDropBetweenOkReadings"


def build_compact_request_payload(output_filename: str) -> list[dict]:
    """Single tumbling-window task fed by the compact custom source."""
    return [
        {
            "name": "custom_compact_source_tumbling",
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
