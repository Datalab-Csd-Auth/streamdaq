from dataclasses import dataclass
from statistics import median
from typing import ClassVar

from streamdaq.measures.numeric.deltas_tuple import DeltasTuple
from streamdaq.utils.picklable import Lambda


@dataclass
class MedianDelta(DeltasTuple):
    _aggregator: ClassVar = Lambda(lambda elements: median(elements) if len(elements) > 0 else 0)
    _result_dtype: ClassVar[type] = float
