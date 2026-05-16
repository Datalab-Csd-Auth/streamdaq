from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

import pathway as pw

from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.translators.string_to_callable import string_to_callable
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@pw.udf
def _user_defined_function(*values, columns, callable) -> bool:
    dict_input = {column: value for column, value in zip(values, columns)}
    return callable(dict_input)


@dataclass
class Row(InstantDataQualityCheck):
    must_be: Callable[[dict[str, Any]], bool] | str
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def __post_init__(self):
        if isinstance(self.must_be, Callable):
            return

        self.must_be = string_to_callable(str(self.must_be))

    def get_measurement_expression(self) -> pw.ColumnExpression:
        columns = []  # TODO FIND A WAY TO GET THE COLUMN NAMES HERE PROBABLY FROM THE TASK
        return _user_defined_function(
            *pw.this,  # TODO THIS WILL NOT WORK, WE NEED THE ACTUAL COLUMN REFERENCES
            columns=columns,
            callable=self.must_be,
        )
