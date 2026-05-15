import pytest

from streamdaq.measures.any_column.sorted_tuple_time import _sort_values_by_timestamp


class TestSortValuesByTimestamp:
    @pytest.mark.parametrize(
        "values, timestamps, expected",
        [
            ((10, 20, 30), (3, 1, 2), (20, 30, 10)),
            (("a", "b", "c"), (2, 1, 3), ("b", "a", "c")),
            ((42,), (1,), (42,)),
            ((1, 2, 3), (1, 2, 3), (1, 2, 3)),
            ((1, 2, 3), (3, 2, 1), (3, 2, 1)),
        ],
        ids=[
            "unsorted_integers",
            "unsorted_strings",
            "single_element",
            "already_sorted",
            "reverse_order",
        ],
    )
    def test_sorts_values_by_corresponding_timestamps(self, values, timestamps, expected):
        assert _sort_values_by_timestamp(values, timestamps) == expected
