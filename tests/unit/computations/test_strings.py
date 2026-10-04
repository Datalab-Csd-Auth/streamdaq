import pytest

from streamdaq.computations.strings import regex_conformance_count, strings_to_length


class TestStringsToLength:
    def test_normal_strings(self):
        assert strings_to_length(["hello", "world"]) == [5, 5]

    def test_varying_lengths(self):
        assert strings_to_length(["a", "bb", "ccc"]) == [1, 2, 3]

    def test_empty_strings(self):
        assert strings_to_length(["", "a", ""]) == [0, 1, 0]

    def test_empty_list(self):
        assert strings_to_length([]) == []

    def test_single_string(self):
        assert strings_to_length(["hello"]) == [5]

    def test_unicode(self):
        assert strings_to_length(["café", "naïve"]) == [4, 5]

    def test_scalar_string(self):
        assert strings_to_length("hello") == [5]

    @pytest.mark.parametrize(
        "elements, expected",
        [
            ([""], [0]),
            (["a" * 100], [100]),
            (["foo", "ba", "z"], [3, 2, 1]),
        ],
    )
    def test_parametrized(self, elements, expected):
        assert strings_to_length(elements) == expected

    @pytest.mark.parametrize(
        "elements, expected",
        [
            ([1, 22, 333], [1, 2, 3]),
            ([1.5, 22.33], [3, 5]),
            ([True, False], [4, 5]),
            ([None, "a"], [4, 1]),
            ([42, "hello", 3.14], [2, 5, 4]),
        ],
        ids=["ints", "floats", "booleans", "none", "mixed"],
    )
    def test_non_string_inputs(self, elements, expected):
        assert strings_to_length(elements) == expected


class TestRegexConformanceCount:
    def test_simple_pattern_partial(self):
        assert regex_conformance_count(["abc", "def", "abz"], r"ab") == 2

    def test_all_match(self):
        assert regex_conformance_count(["abc", "abd", "abe"], r"ab.") == 3

    def test_none_match(self):
        assert regex_conformance_count(["abc", "def"], r"^xyz") == 0

    def test_empty_elements(self):
        assert regex_conformance_count([], r".*") == 0

    def test_empty_string_elements(self):
        assert regex_conformance_count(["", "a", ""], r"^$") == 2

    def test_case_sensitive(self):
        assert regex_conformance_count(["Abc", "abc", "ABC"], r"abc") == 1

    def test_email_pattern(self):
        elements = ["user@example.com", "bad-email", "foo@bar.org"]
        assert regex_conformance_count(elements, r"[^@]+@[^@]+\.[^@]+") == 2

    def test_digit_pattern(self):
        assert regex_conformance_count(["123", "abc", "456"], r"\d+") == 2

    @pytest.mark.parametrize(
        "pattern, elements, expected",
        [
            (r"\d{3}", ["123", "12", "1234", "abc"], 2),
            (r"[A-Z]", ["Hello", "hello", "HELLO"], 2),
            (r"^a.*z$", ["abz", "az", "bz", "abc"], 2),
        ],
    )
    def test_common_patterns(self, pattern, elements, expected):
        assert regex_conformance_count(elements, pattern) == expected
