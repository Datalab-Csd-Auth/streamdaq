import pytest

from streamdaq.custom import measure
from streamdaq.measures.registry import MEASURE_REGISTRY


class TestCustomRegistration:
    """The decorator registers the class under the resolved measure name."""

    def test_name_defaults_to_function_name(self):
        @measure(["x"])
        def _defaulted_sum(d):
            return sum(d["x"])

        assert MEASURE_REGISTRY["_defaulted_sum"] is _defaulted_sum

    def test_explicit_name_overrides_function_name(self):
        @measure(["x"], name="_ExplicitlyNamed")
        def _source_function_name(d):
            return sum(d["x"])

        assert MEASURE_REGISTRY["_ExplicitlyNamed"] is _source_function_name
        assert "_source_function_name" not in MEASURE_REGISTRY


_POST_INIT_CASES = [
    ("empty-columns", [], None, "empty columns"),
    ("duplicate-columns", ["a", "a"], None, "duplicates"),
    ("sort-column-not-in-columns", ["a", "b"], "c", "not in the columns"),
]


class TestCustomValidation:
    """``__post_init__`` rejects inconsistent column configurations."""

    @pytest.mark.parametrize(
        "columns, sort_by_column, match",
        [(cols, sort_by, match) for (_id, cols, sort_by, match) in _POST_INIT_CASES],
        ids=[case[0] for case in _POST_INIT_CASES],
    )
    def test_post_init_raises(self, columns, sort_by_column, match):
        measure(columns, name="_InvalidCustomMeasure", sort_by_column=sort_by_column)(
            lambda d: None
        )
        with pytest.raises(ValueError, match=match):
            MEASURE_REGISTRY["_InvalidCustomMeasure"]()


class TestCustomExports:
    """The public re-export chain resolves to a single decorator object."""

    def test_reexports_are_the_same_object(self):
        from streamdaq.custom import measure as top_level
        from streamdaq.custom._measures import measure as subpackage
        from streamdaq.custom._measures.decorator import measure as origin

        assert top_level is subpackage is origin


class TestSpawnSafety:
    """The decorator stores ``measurement_function`` as a static method for MacOS compatibility."""

    def test_measurement_function_is_stored_as_staticmethod(self):
        @measure(["value"], name="_MeanOfPositiveReadings")
        def _mean_of_positive_readings(d):
            positives = [value for value in d["value"] if value > 0]
            return sum(positives) / len(positives)

        measure_class = MEASURE_REGISTRY["_MeanOfPositiveReadings"]

        assert type(measure_class.__dict__["measurement_function"]) is staticmethod
        assert measure_class().measurement_function({"value": [2.0, -3.0, 4.0]}) == 3.0
