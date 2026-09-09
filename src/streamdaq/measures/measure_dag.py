"""Helpers for assembling the Pathway DAG that computes a single measure.

A :class:`~streamdaq.measures.base.DataQualityMeasure` computes its value in up to
two phases:

1. a *reduce* phase, described by :meth:`DataQualityMeasure.get_reduce_kwargs`, which
   produces either the measure's own reduced column (keyed by the "overridable
   placeholder" name) or the shared columns of its dependencies; and
2. an optional *expression* phase, described by :meth:`DataQualityMeasure.get_expression`,
   which computes the final value on top of the reduced columns.

This module owns that assembly so the contract lives in exactly one place. Both the
runtime engine and tests can compute a measure over a table without re-implementing
the two-phase wiring.
"""

import pathway as pw

from streamdaq.measures.base import DataQualityMeasure

RESULT_COLUMN = "result"


def build_measure_dag(
    table: pw.Table, measure: DataQualityMeasure, result_column: str = RESULT_COLUMN
) -> pw.Table:
    """Compute ``measure`` over ``table`` and return a table with a single result column.

    The table is reduced (grouping all rows into one) using the measure's reduce kwargs,
    then, if the measure defines a second-layer expression, that expression is applied.
    Measures without an expression phase expose their value directly through the reduced
    "overridable placeholder" column.

    Args:
        table: The input table to compute the measure over.
        measure: The measure to compute.
        result_column: Name of the single output column. Defaults to ``"result"``.

    Returns:
        A table with exactly one column, ``result_column``, holding the measure's value.
    """
    reduced = table.reduce(**measure.get_reduce_kwargs())

    expression = measure.get_expression()
    if expression is not None:
        return reduced.with_columns(**{result_column: expression}).select(pw.this[result_column])

    placeholder = DataQualityMeasure._get_internal_overridable_placeholder_column_name()
    return reduced.select(**{result_column: pw.this[placeholder]})
