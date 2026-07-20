import pathway as pw

from streamdaq import checks, measures
from streamdaq.utils.api import (
    build_csv_input,
    build_kafka_input,
    build_mqtt_input,
    build_parquet_input,
    build_python_connector_input,
)

INPUT_REGISTRY = {
    "csv": build_csv_input,  # static or streaming
    "parquet": build_parquet_input,  # static or streaming
    "python_connector": build_python_connector_input,  # streaming
    "kafka": build_kafka_input,  # streaming
    "mqtt": build_mqtt_input,  # streaming
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
