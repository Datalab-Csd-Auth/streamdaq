from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

import pathway as pw

from streamdaq.api.registries import MEASURE_REGISTRY
from streamdaq.computations.generic import sort_lists_by
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass(kw_only=True)
class CustomDataQualityMeasure(DataQualityMeasure):
    name: str
    columns: list[str]
    measurement_function: Callable[[list[list[Any]]], Any]
    sort_by_column: str | None = None
    desc: bool = False
    _dependencies: ClassVar[list[type[DataQualityMeasure]]] = []
    _applicability: ClassVar[DataTypeApplicability] = None
    column: str = ""  # intentional to ingnore this field coming from the superclass

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "__abstractmethods__", None) is not None:
            return
        MEASURE_REGISTRY[cls.__name__] = cls

    def __post_init__(self):
        if len(self.columns) == 0:
            raise ValueError("Cannot initialize a custom data quality measure on empty columns.")

        if len(set(self.columns)) != len(self.columns):
            raise ValueError(
                f"Cannot initialize a custom data quality measure on columns `{self.columns}` "
                f"because it contains duplicates."
            )

        if self.sort_by_column and self.sort_by_column not in self.columns:
            raise ValueError(
                f"Cannot initialize a custom data quality measure on columns `{self.columns}` "
                f"sorted by '{self.sort_by_column}': '{self.sort_by_column}' not in the columns."
            )

    def get_reduce_kwargs(self) -> dict[str, pw.ColumnExpression]:
        reduce_kwargs = super().get_reduce_kwargs()
        for column in self.columns:
            additional_kw = Tuple._get_internal_shared_column_name(column)
            reduce_kwargs[additional_kw] = Tuple(column).get_reducer()

        return reduce_kwargs

    def get_expression(self) -> pw.ColumnExpression:
        additional_args = [
            pw.this[Tuple._get_internal_shared_column_name(column)] for column in self.columns
        ]

        def custom_measurement_function(
            *values_lists,
            column_names: list[str],
            sort_by_column: str | None,
            desc: bool,
        ):
            context: dict[str, Any] = dict()

            if sort_by_column:
                values_lists = sort_lists_by(
                    *values_lists, key_list=column_names.index(sort_by_column), desc=desc
                )

            for column_name, values_list in zip(column_names, values_lists):
                context[column_name] = values_list
            return self.measurement_function(context)

        return pw.apply(
            custom_measurement_function,
            *additional_args,
            column_names=self.columns,
            sort_by_column=self.sort_by_column,
            desc=self.desc,
        )
