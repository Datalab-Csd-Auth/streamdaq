from dataclasses import dataclass
from typing import ClassVar

from streamdaq.measures.numeric.deltas_tuple import DeltasTuple
from streamdaq.utils.picklable import Lambda


@dataclass
class MinDelta(DeltasTuple):
    _aggregator: ClassVar = Lambda(lambda elements: min(elements) if len(elements) > 0 else 0)
    _result_dtype: ClassVar[type] = float
