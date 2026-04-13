import pytest

from streamdaq.utils.validation import ensure_iterable


def test_ensure_iterable_with_list():
    data = [1, 2, 3]
    assert ensure_iterable(data) is data


def test_ensure_iterable_with_tuple():
    data = (1, 2, 3)
    assert ensure_iterable(data) is data


def test_ensure_iterable_with_set():
    data = {1, 2, 3}
    assert ensure_iterable(data) is data


def test_ensure_iterable_with_generator():
    gen = (x for x in range(3))
    assert ensure_iterable(gen) is gen


def test_ensure_iterable_with_empty_list():
    assert ensure_iterable([]) == []


def test_ensure_iterable_with_string():
    result = ensure_iterable("hello")
    assert result == ("hello",)


def test_ensure_iterable_with_empty_string():
    result = ensure_iterable("")
    assert result == ("",)


@pytest.mark.parametrize(
    "scalar, expected",
    [
        (42, (42,)),
        (3.14, (3.14,)),
        (True, (True,)),
        (0, (0,)),
    ],
)
def test_ensure_iterable_with_scalar(scalar, expected):
    assert ensure_iterable(scalar) == expected


def test_ensure_iterable_with_none_raises_type_error():
    with pytest.raises(TypeError, match="Input cannot be None"):
        ensure_iterable(None)
