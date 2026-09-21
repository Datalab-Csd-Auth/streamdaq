from collections.abc import Callable
from typing import Any

Assessment = Callable[[Any], bool]

ASSESSMENT_REGISTRY: dict[str, Assessment] = {}
