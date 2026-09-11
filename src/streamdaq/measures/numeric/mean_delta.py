from dataclasses import dataclass
from statistics import mean
from typing import ClassVar

from streamdaq.measures.numeric.deltas_tuple import DeltasTuple
from streamdaq.utils.picklable import Lambda


@dataclass
class MeanDelta(DeltasTuple):
    _aggregator: ClassVar = Lambda(lambda elements: mean(elements) if len(elements) > 0 else 0)
    _result_dtype: ClassVar[type] = float
