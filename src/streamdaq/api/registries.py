import functools

import pathway as pw

from streamdaq import checks, measures
from streamdaq.utils.api import (
    build_csv_input,
    build_evb_mock_input,
    build_parquet_input,
    build_python_connector_input,
)
from streamdaq.utils.picklable import Lambda

INPUT_REGISTRY = {
    "evb_mock": build_evb_mock_input,
    "python_connector": build_python_connector_input,
    "csv": build_csv_input,
    "parquet": build_parquet_input,
    "kafka": Lambda(lambda params: functools.partial(pw.io.kafka.read, **params)),
    "mqtt": Lambda(lambda params: functools.partial(pw.io.mqtt.read, **params)),
}

OUTPUT_REGISTRY = {
    "jsonlines": pw.io.jsonlines.write,
    "csv": pw.io.csv.write,
    "postgres": pw.io.postgres.write,
    "mqtt": pw.io.mqtt.write,
    "kafka": pw.io.kafka.write,
}

# --- Windows ---
# TODO: This will change to StreamDaQ windows
WINDOW_REGISTRY = {
    "sliding": pw.temporal.sliding,
    "tumbling": pw.temporal.tumbling,
}

# --- Checks & Measures ---

# Automatically build the registry of all available instant checks
INSTANT_CHECK_REGISTRY = {
    name: getattr(checks, name) for name in checks.__all__ if name != "WindowDataQualityCheck"
}

# Automatically build the registry of all available measures
MEASURE_REGISTRY = {
    name: getattr(measures, name)
    for name in measures.__all__
    if name not in ("DataQualityMeasure", "RoundableDataQualityMeasure")
}
