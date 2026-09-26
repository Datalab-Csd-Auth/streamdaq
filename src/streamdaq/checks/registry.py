from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from streamdaq.checks.base import DataQualityCheck

INSTANT_CHECK_REGISTRY: dict[str, "DataQualityCheck"] = {}
