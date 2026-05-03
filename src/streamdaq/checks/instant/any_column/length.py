from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

import pathway as pw

from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.translators.string_to_callable import string_to_callable
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Length(InstantDataQualityCheck):
    must_be: Callable[[Any], bool] | str
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def __post_init__(self):
        if isinstance(self.must_be, Callable):
            return

        self.must_be = string_to_callable(str(self.must_be))

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda value: self.must_be(len(str(value))), bool, pw.this[self.column]
        )
