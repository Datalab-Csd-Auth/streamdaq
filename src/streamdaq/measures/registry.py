from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from streamdaq.measures.base import DataQualityMeasure

MEASURE_REGISTRY: dict[str, "DataQualityMeasure"] = {}
