import pathway as pw

from streamdaq import checks, measures
from streamdaq.io.sinks import SINK_REGISTRY
from streamdaq.io.sources import SOURCE_REGISTRY

__all__ = [
    "SOURCE_REGISTRY",
    "INSTANT_CHECK_REGISTRY",
    "MEASURE_REGISTRY",
    "SINK_REGISTRY",
    "WINDOW_REGISTRY",
]

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
