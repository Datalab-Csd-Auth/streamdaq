from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import DataQualityMeasure
from streamdaq.reducers.most_frequent_approx import most_frequent_approx_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class MostFrequentApprox(DataQualityMeasure):
    """Approximate most-frequent values, computed with a streaming frequent-items sketch.

    Returns the values tied for the maximum estimated frequency, as a tuple.
    This implementation adopts an _approximate_ computation. For an exact result alternative see
    :class:`~streamdaq.measures.any_column.most_frequent.MostFrequent`.
    """

    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def get_reducer(self) -> pw.ColumnExpression:
        return most_frequent_approx_reducer(pw.this[self.column])
