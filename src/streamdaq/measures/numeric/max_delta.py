from dataclasses import dataclass
from typing import ClassVar

from streamdaq.measures.numeric.deltas_tuple import DeltasTuple
from streamdaq.utils.picklable import Lambda


@dataclass
class MaxDelta(DeltasTuple):
    _aggregator: ClassVar = Lambda(lambda elements: max(elements) if len(elements) > 0 else 0)
    _result_dtype: ClassVar[type] = float
