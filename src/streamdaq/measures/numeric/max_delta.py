from dataclasses import dataclass
from typing import ClassVar

from streamdaq.measures.numeric.deltas_tuple import DeltasTuple


@dataclass
class MaxDelta(DeltasTuple):
    _aggregator: ClassVar = lambda elements: max(elements) if len(elements) > 0 else 0
    _result_dtype: ClassVar[type] = float
