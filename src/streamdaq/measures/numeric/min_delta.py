from dataclasses import dataclass
from typing import ClassVar

from streamdaq.measures.numeric.deltas_tuple import DeltasTuple


@dataclass
class MinDelta(DeltasTuple):
    _aggregator: ClassVar = lambda elements: min(elements) if len(elements) > 0 else 0
    _result_dtype: ClassVar[type] = float
