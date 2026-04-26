import pytest

from streamdaq.reducers.distinct_count_approx import _DistinctCountApproxReducer
from streamdaq.reducers.most_frequent_approx import _MostFrequentApproxReducer
from streamdaq.reducers.std_dev import _StdDevReducer


class TestStdDevReducer:
    def test_from_row(self):
        r = _StdDevReducer.from_row([5.0])
        assert r.count == 1
        assert r.sum == 5.0
        assert r.sum_squares == 25.0

    def test_known_population_variance(self):
        values = [2, 4, 4, 4, 5, 5, 7, 9]  # variance = 4.0
        acc = _StdDevReducer.from_row([values[0]])
        for v in values[1:]:
            acc.update(_StdDevReducer.from_row([v]))
        assert acc.compute_result() == pytest.approx(4.0)

    def test_uniform_zero_variance(self):
        values = [3, 3, 3, 3]
        acc = _StdDevReducer.from_row([values[0]])
        for v in values[1:]:
            acc.update(_StdDevReducer.from_row([v]))
        assert acc.compute_result() == 0.0

    def test_single_value(self):
        acc = _StdDevReducer.from_row([7])
        assert acc.compute_result() == 0.0

    def test_retract(self):
        values = [2, 4, 4, 4, 5, 5, 7, 9]
        acc = _StdDevReducer.from_row([values[0]])
        for v in values[1:]:
            acc.update(_StdDevReducer.from_row([v]))
        acc.retract(_StdDevReducer.from_row([9]))
        expected_acc = _StdDevReducer.from_row([2])
        for v in [4, 4, 4, 5, 5, 7]:
            expected_acc.update(_StdDevReducer.from_row([v]))
        assert acc.compute_result() == pytest.approx(expected_acc.compute_result())

    def test_negative_values(self):
        values = [-3, -1, 1, 3]  # mean=0, var=(9+1+1+9)/4=5.0
        acc = _StdDevReducer.from_row([values[0]])
        for v in values[1:]:
            acc.update(_StdDevReducer.from_row([v]))
        assert acc.compute_result() == pytest.approx(5.0)

    def test_floating_point(self):
        values = [0.1, 0.2, 0.3]
        acc = _StdDevReducer.from_row([values[0]])
        for v in values[1:]:
            acc.update(_StdDevReducer.from_row([v]))
        # mean=0.2, var = ((0.01+0+0.01)/3) = 0.00666...
        assert acc.compute_result() == pytest.approx(0.00666666, abs=1e-6)

    def test_retract_all_raises_zero_division(self):
        # Retracting all elements leaves count=0, which causes ZeroDivisionError
        acc = _StdDevReducer.from_row([5.0])
        acc.retract(_StdDevReducer.from_row([5.0]))
        assert acc.count == 0
        with pytest.raises(ZeroDivisionError):
            acc.compute_result()


class TestDistinctCountApproxReducer:
    def test_from_row_single(self):
        r = _DistinctCountApproxReducer.from_row(["hello"])
        assert r.compute_result() == pytest.approx(1.0, abs=1)

    def test_merge_distinct(self):
        values = [str(i) for i in range(1000)]
        acc = _DistinctCountApproxReducer.from_row([values[0]])
        for v in values[1:]:
            acc.update(_DistinctCountApproxReducer.from_row([v]))
        assert acc.compute_result() == pytest.approx(1000, rel=0.05)

    def test_duplicates_deduplicated(self):
        values = ["a"] * 50 + ["b"] * 50
        acc = _DistinctCountApproxReducer.from_row([values[0]])
        for v in values[1:]:
            acc.update(_DistinctCountApproxReducer.from_row([v]))
        assert acc.compute_result() == pytest.approx(2, abs=1)

    def test_non_string_coercion(self):
        r = _DistinctCountApproxReducer.from_row([123])
        assert r.compute_result() == pytest.approx(1.0, abs=1)


class TestMostFrequentApproxReducer:
    def test_from_row_single(self):
        r = _MostFrequentApproxReducer.from_row(["apple"])
        result = r.compute_result()
        items = [item[0] for item in result]
        assert "apple" in items

    def test_dominant_item(self):
        values = ["a"] * 20 + ["b"]
        acc = _MostFrequentApproxReducer.from_row([values[0]])
        for v in values[1:]:
            acc.update(_MostFrequentApproxReducer.from_row([v]))
        result = acc.compute_result()
        items = [item[0] for item in result]
        assert "a" in items

    def test_compute_result_type(self):
        r = _MostFrequentApproxReducer.from_row(["x"])
        result = r.compute_result()
        assert isinstance(result, (list, tuple))

    def test_multiple_update_cycles_preserve_state(self):
        # Build up a sketch over many updates, verify it doesn't corrupt
        acc = _MostFrequentApproxReducer.from_row(["dominant"])
        for _ in range(30):
            acc.update(_MostFrequentApproxReducer.from_row(["dominant"]))
        for i in range(5):
            acc.update(_MostFrequentApproxReducer.from_row([f"rare_{i}"]))
        result = acc.compute_result()
        items = [item[0] for item in result]
        assert "dominant" in items

    def test_many_distinct_items(self):
        # With k=3, only the most frequent items should survive
        acc = _MostFrequentApproxReducer.from_row(["top"])
        for _ in range(50):
            acc.update(_MostFrequentApproxReducer.from_row(["top"]))
        for i in range(20):
            acc.update(_MostFrequentApproxReducer.from_row([f"noise_{i}"]))
        result = acc.compute_result()
        items = [item[0] for item in result]
        assert "top" in items
