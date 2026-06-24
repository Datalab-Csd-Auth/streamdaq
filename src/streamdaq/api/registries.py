import pathway as pw

from streamdaq import checks, measures

# --- Inputs & Outputs ---

INPUT_REGISTRY = {
    "markdown_table": lambda params: (
        lambda **kwargs: pw.debug.table_from_markdown(params["markdown"])
    ),
    "csv": lambda params: lambda **kwargs: pw.io.csv.read(**params),
    "kafka": lambda params: lambda **kwargs: pw.io.kafka.read(**params),
    "mqtt": lambda params: lambda **kwargs: pw.io.mqtt.read(**params),
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
