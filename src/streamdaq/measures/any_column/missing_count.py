from dataclasses import dataclass, field
from typing import Any, ClassVar, Self

import pathway as pw

from streamdaq.computations.generic import set_conformance_count
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class MissingCount(DataQualityMeasure):
    disguised: list[Any] = field(default_factory=lambda: [])
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _explicit_missing_values: ClassVar[list[Any | None]] = [None, ""]
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def _concatenate_explicit_diguised_values(self):
        if not self.disguised:
            return set(self._explicit_missing_values)
        return set(self._explicit_missing_values + self.disguised)

    def get_reducer(self) -> pw.ColumnExpression:
        all_missing_values = self._concatenate_explicit_diguised_values()
        return pw.apply_with_type(
            lambda elements: set_conformance_count(elements, all_missing_values),
            int,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
