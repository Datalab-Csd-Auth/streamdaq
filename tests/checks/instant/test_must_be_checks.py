import pytest

from streamdaq.api.models import InstantCheckConfig
from streamdaq.checks.instant.any_column.length import Length
from streamdaq.checks.instant.any_column.value import Value


class TestMustBeValidation:
    @pytest.mark.parametrize("check_cls", [Length, Value])
    def test_valid_string_is_accepted_and_kept_as_string(self, check_cls):
        check = check_cls(name="c", column="x", must_be="<= 4")
        assert check.must_be == "<= 4"

    @pytest.mark.parametrize("check_cls", [Length, Value])
    def test_callable_is_accepted(self, check_cls):
        predicate = check_cls(name="c", column="x", must_be=lambda v: v < 3)
        assert callable(predicate.must_be)

    @pytest.mark.parametrize("check_cls", [Length, Value])
    @pytest.mark.parametrize("bad_must_be", ["garbage", "??", 123, None])
    def test_invalid_must_be_is_rejected_at_construction(self, check_cls, bad_must_be):
        with pytest.raises(ValueError):
            check_cls(name="c", column="x", must_be=bad_must_be)

    @pytest.mark.parametrize("check_class", ["Length", "Value"])
    def test_api_config_keeps_must_be_serializable(self, check_class):
        config = InstantCheckConfig(
            check_class=check_class, name="c", params={"column": "x", "must_be": "<= 4"}
        )
        assert config.params["must_be"] == "<= 4"
