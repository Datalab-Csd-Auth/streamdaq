from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.computations.generic import most_frequent_elements
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class MostFrequent(DataQualityMeasure):
    """Exact most-frequent values in a column.

    Returns every value tied for the maximum frequency, as a tuple (e.g. a column
    containing ``a, a, b, b, c`` yields ``("a", "b")``). This measure adopts an _exact_
    computation. For an approximate, sketch-based alternative use
    :class:`~streamdaq.measures.any_column.most_frequent_approx.MostFrequentApprox`.
    """

    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[DataQualityMeasure]]] = [Tuple]

    def get_expression(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            Lambda(most_frequent_elements),
            tuple,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
