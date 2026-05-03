import pathway as pw
from pydantic import ValidationError

from streamdaq.schema.evb.definitions import (
    _VALID_TIME_DIGITS,
    EVBKeyNames,
    ValidatableEVBSchema,
    _StreamdaqInternalColumnNames,
)
from streamdaq.schema.evb.lambda_factory import LambdaFactory as Lambda

__EMPTY_STRING = ""


def _validate_with_pydantic(raw_evb: tuple[pw.Json]) -> str | None:
    try:
        ValidatableEVBSchema(**_Transform.to_pydantic_validatable(raw_evb))
        return None
    except ValidationError as e:
        return str(e)


def _construct_validation_errors_report_if_needed(
    pydantic_errors: str, is_time_first_field: bool, is_time_valid: bool
) -> dict[str, str | bool] | None:
    if not pydantic_errors and is_time_first_field and is_time_valid:
        return None

    report = dict()
    if pydantic_errors:
        report[_StreamdaqInternalColumnNames.PYDANTIC_ERRORS] = pydantic_errors
    if not is_time_first_field:
        report[_StreamdaqInternalColumnNames.IS_TIME_FIRST_FIELD] = (is_time_first_field,)
    if not is_time_valid:
        report[_StreamdaqInternalColumnNames.IS_TIME_VALID] = (is_time_valid,)
    return report


class _Transform:
    @classmethod
    def to_pydantic_validatable(cls, raw_evb: tuple[pw.Json]) -> dict[str, pw.ColumnExpression]:
        return {EVBKeyNames.MEASUREMENTS: [pw_json.as_dict() for pw_json in raw_evb]}

    @classmethod
    def explode_top_level(cls) -> dict[str, pw.ColumnExpression]:
        return {
            EVBKeyNames.NAME: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.NAME].as_str(),
            EVBKeyNames.TAGS: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.TAGS],
            EVBKeyNames.TYPE: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.TYPE].as_str(),
            EVBKeyNames.FIELDS: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.FIELDS],
            EVBKeyNames.VALUES: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.VALUES],
        }

    @classmethod
    def enrich_with_pydantic_errors(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.PYDANTIC_ERRORS: pw.apply_with_type(
                _validate_with_pydantic, str | None, pw.this[EVBKeyNames.MEASUREMENTS]
            )
        }

    @classmethod
    def enrich_with_fields_validation(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.IS_TIME_FIRST_FIELD: pw.apply_with_type(
                Lambda.check_nth_list_element_equals_value(0, "time", str),
                bool,
                pw.this[EVBKeyNames.FIELDS],
            ),
        }

    @classmethod
    def extract_time_from_fields_values(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.TIME: pw.apply_with_type(
                Lambda.get_nth_list_element(0, int), int, pw.this.values
            ),
            EVBKeyNames.VALUES: pw.apply_with_type(
                Lambda.get_list_elements_from_n_to_end(1, float),
                list[float],
                pw.this[EVBKeyNames.VALUES],
            ),
            EVBKeyNames.FIELDS: pw.apply_with_type(
                Lambda.get_list_elements_from_n_to_end(1, str),
                list[str],
                pw.this[EVBKeyNames.FIELDS],
            ),
        }

    @classmethod
    def enrich_with_time_validation(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.IS_TIME_VALID: pw.apply_with_type(
                Lambda.check_int_has_exact_nof_digits(_VALID_TIME_DIGITS),
                bool,
                pw.this[_StreamdaqInternalColumnNames.TIME],
            ),
        }

    @classmethod
    def to_native(
        cls, native_evb_schema: tuple[tuple[str, type]]
    ) -> dict[str, pw.ColumnExpression]:
        return {
            column_name: pw.apply_with_type(Lambda.get_nth_list_element(idx), dtype, pw.this.values)
            for idx, (column_name, dtype) in enumerate(native_evb_schema)
        }

    @classmethod
    def enrich_with_validation_errors_report(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.VALIDATION_ERRORS_REPORT: pw.apply_with_type(
                _construct_validation_errors_report_if_needed,
                dict[str, str | bool] | None,
                pw.this[_StreamdaqInternalColumnNames.PYDANTIC_ERRORS],
                pw.this[_StreamdaqInternalColumnNames.IS_TIME_FIRST_FIELD],
                pw.this[_StreamdaqInternalColumnNames.IS_TIME_VALID],
            )
        }

    @classmethod
    def cleanup_column_names(cls) -> list[str]:
        return [
            EVBKeyNames.MEASUREMENTS,
            EVBKeyNames.VALUES,
            EVBKeyNames.FIELDS,
            _StreamdaqInternalColumnNames.PYDANTIC_ERRORS,
            _StreamdaqInternalColumnNames.IS_TIME_FIRST_FIELD,
            _StreamdaqInternalColumnNames.IS_TIME_VALID,
        ]


def convert_raw_evb_to_native_format(
    raw_evb_table: pw.Table, native_evb_schema: tuple[tuple[str, type]]
) -> pw.Table:
    return (
        raw_evb_table.with_columns(**_Transform.enrich_with_pydantic_errors())
        .flatten(pw.this[EVBKeyNames.MEASUREMENTS])
        .with_columns(**_Transform.explode_top_level())
        .flatten(pw.this[EVBKeyNames.VALUES])
        .with_columns(**_Transform.enrich_with_fields_validation())
        .with_columns(**_Transform.extract_time_from_fields_values())
        .with_columns(**_Transform.enrich_with_time_validation())
        .with_columns(**_Transform.enrich_with_validation_errors_report())
        .with_columns(**_Transform.to_native(native_evb_schema))
        .without(*_Transform.cleanup_column_names())
    )
