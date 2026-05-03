from dataclasses import dataclass

from streamdaq.checks.base import DataQualityCheck


@dataclass
class WindowDataQualityCheck(DataQualityCheck): ...
