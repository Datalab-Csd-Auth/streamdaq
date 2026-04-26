from dataclasses import dataclass, field
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import percentiles_dict
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Percentiles(RoundableDataQualityMeasure):
    percentiles: list[int] = field(default_factory=lambda: [25, 50, 75])
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            percentiles_dict,
            dict,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
            self.percentiles,
            self.precision,
        )
