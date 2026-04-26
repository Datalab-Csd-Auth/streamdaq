from streamdaq.measures.base import DataQualityMeasure, RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


class TestGetInternalSharedColumnName:
    def test_format(self):
        class _DummyMeasure(DataQualityMeasure):
            _applicability = DataTypeApplicability.ANY_COLUMN

            def get_reducer(self):
                pass

        result = _DummyMeasure._get_internal_shared_column_name("age")
        assert result == "__streamdaq_internal_shared_#_DummyMeasure#age"

    def test_different_subclass_different_name(self):
        class _Alpha(DataQualityMeasure):
            _applicability = DataTypeApplicability.ANY_COLUMN

            def get_reducer(self):
                pass

        class _Beta(DataQualityMeasure):
            _applicability = DataTypeApplicability.ANY_COLUMN

            def get_reducer(self):
                pass

        assert _Alpha._get_internal_shared_column_name(
            "x"
        ) != _Beta._get_internal_shared_column_name("x")

    def test_empty_column(self):
        class _Dummy(DataQualityMeasure):
            _applicability = DataTypeApplicability.ANY_COLUMN

            def get_reducer(self):
                pass

        result = _Dummy._get_internal_shared_column_name("")
        assert result.endswith("#")


class TestIsApplicableTo:
    def test_any_column_applicable_to_int(self):
        class _AnyMeasure(DataQualityMeasure):
            _applicability = DataTypeApplicability.ANY_COLUMN

            def get_reducer(self):
                pass

        m = _AnyMeasure(column="x")
        assert m.is_applicable_to(int) is True

    def test_numeric_not_applicable_to_str(self):
        class _NumMeasure(DataQualityMeasure):
            _applicability = DataTypeApplicability.NUMERIC_ONLY

            def get_reducer(self):
                pass

        m = _NumMeasure(column="x")
        assert m.is_applicable_to(str) is False


class TestInitSubclassRegistration:
    def test_subclass_with_applicability_registered(self):
        before = len(DataTypeApplicability.ANY_COLUMN.available_measures)

        class _Registered(DataQualityMeasure):
            _applicability = DataTypeApplicability.ANY_COLUMN

            def get_reducer(self):
                pass

        after = len(DataTypeApplicability.ANY_COLUMN.available_measures)
        assert after == before + 1
        assert _Registered in DataTypeApplicability.ANY_COLUMN.available_measures


class TestRoundableDataQualityMeasure:
    def test_default_precision_none(self):
        class _RoundDummy(RoundableDataQualityMeasure):
            _applicability = DataTypeApplicability.ANY_COLUMN

            def get_reducer(self):
                pass

        m = _RoundDummy(column="x")
        assert m.precision is None

    def test_precision_none_returns_input_unchanged(self):
        class _RoundDummy(RoundableDataQualityMeasure):
            _applicability = DataTypeApplicability.ANY_COLUMN

            def get_reducer(self):
                pass

        m = _RoundDummy(column="x")
        sentinel = object()
        assert m._round_reducer_if_needed(sentinel) is sentinel
