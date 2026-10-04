import pytest

from streamdaq.schema.evb.lambda_factory import LambdaFactory


class TestGetNthListElement:
    def test_returns_first_element(self):
        fn = LambdaFactory.get_nth_list_element(0)
        assert fn(["a", "b", "c"]) == "a"

    def test_returns_nth_element(self):
        fn = LambdaFactory.get_nth_list_element(2)
        assert fn([10, 20, 30]) == 30

    def test_unsupported_dtype_raises(self):
        with pytest.raises(NotImplementedError, match="dtype"):
            LambdaFactory.get_nth_list_element(0, dtype=bytes)

    @pytest.mark.parametrize("dtype", [bool, dict, float, int, list, str])
    def test_supported_dtypes_do_not_raise(self, dtype):
        fn = LambdaFactory.get_nth_list_element(0, dtype=dtype)
        assert callable(fn)


class TestGetListElementsFromNToEnd:
    def test_slices_from_n(self):
        fn = LambdaFactory.get_list_elements_from_n_to_end(1)
        assert fn(["time", "temp", "humidity"]) == ["temp", "humidity"]

    def test_slices_from_zero(self):
        fn = LambdaFactory.get_list_elements_from_n_to_end(0)
        assert fn([1, 2, 3]) == [1, 2, 3]

    def test_n_beyond_length_returns_empty(self):
        fn = LambdaFactory.get_list_elements_from_n_to_end(10)
        assert fn([1, 2, 3]) == []

    def test_unsupported_dtype_raises(self):
        with pytest.raises(NotImplementedError, match="dtype"):
            LambdaFactory.get_list_elements_from_n_to_end(0, dtype=bytes)

    @pytest.mark.parametrize("dtype", [bool, dict, float, int, list, str])
    def test_supported_dtypes_do_not_raise(self, dtype):
        fn = LambdaFactory.get_list_elements_from_n_to_end(0, dtype=dtype)
        assert callable(fn)


class TestCheckNthListElementEqualsValue:
    def test_returns_true_when_match(self):
        fn = LambdaFactory.check_nth_list_element_equals_value(0, "time")
        assert fn(["time", "temp"]) is True

    def test_returns_false_when_no_match(self):
        fn = LambdaFactory.check_nth_list_element_equals_value(0, "time")
        assert fn(["temp", "time"]) is False

    def test_with_integer_value(self):
        fn = LambdaFactory.check_nth_list_element_equals_value(1, 42)
        assert fn([0, 42, 99]) is True


class TestCheckIntHasExactNofDigits:
    @pytest.mark.parametrize(
        "value, nof_digits, expected",
        [
            (1645334535000, 13, True),
            (164533453500, 13, False),
            (16453345350000, 13, False),
            (123, 3, True),
            (99, 3, False),
            (1000, 3, False),
            (0, 1, True),
            (9, 1, True),
            (10, 1, False),
        ],
    )
    def test_digit_count(self, value, nof_digits, expected):
        fn = LambdaFactory.check_int_has_exact_nof_digits(nof_digits)
        assert fn(value) is expected

    def test_negative_number_includes_sign(self):
        # Documents current behavior: str(-123) has length 4 (includes '-')
        fn = LambdaFactory.check_int_has_exact_nof_digits(3)
        assert fn(-123) is False  # len(str(-123)) == 4, not 3
