from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

import pathway as pw

from streamdaq.checks.base import DataQualityCheck
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.translators.string_to_callable import string_to_callable
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class WindowDataQualityCheck(DataQualityCheck):
    measure: DataQualityMeasure
    must_be: Callable[[Any], bool] | str
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def __post_init__(self):
        if isinstance(self.must_be, Callable):
            return

        self.must_be = string_to_callable(str(self.must_be))

    def get_reduce_kwargs(self) -> dict[str, pw.ColumnExpression]:
        reduce_kwargs = self.measure.get_reduce_kwargs()

        overridable_column = DataQualityMeasure._get_internal_overridable_placeholder_column_name()
        if overridable_column not in reduce_kwargs:
            return reduce_kwargs

        # if the overridable column name is present as key, override/replace it with the check name
        reduce_kwargs[self.name] = reduce_kwargs.pop(overridable_column)
        return reduce_kwargs

    def get_measurement_expression(self) -> pw.ColumnExpression | None:
        return self.measure.get_expression()

    def get_assessment_expression(self) -> pw.ColumnExpression:
        return pw.apply_with_type(self.must_be, bool, pw.this[self.name])
