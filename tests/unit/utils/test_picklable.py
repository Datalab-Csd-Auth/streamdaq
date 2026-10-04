"""Tests for the ``Lambda`` picklable wrapper."""

import dill

from streamdaq.utils.picklable import IS_RUNNING_ON_MAC, Lambda, PicklableLambda


class TestLambdaCall:
    def test_wraps_and_calls_lambda(self):
        wrapped = Lambda(lambda x: x * 2)
        assert wrapped(21) == 42

    def test_forwards_args_and_kwargs(self):
        wrapped = Lambda(lambda a, b, c=0: a + b + c)
        assert wrapped(1, 2, c=3) == 6


class TestLambdaSerialization:
    """The reason ``Lambda`` exists: a local lambda surviving ``dill`` across processes."""

    def test_local_lambda_survives_dill_round_trip(self):
        wrapped = Lambda(lambda x: x * 2)
        restored = dill.loads(dill.dumps(wrapped))
        assert restored(21) == 42


class TestPicklableLambdaWrapper:
    """macOS-specific behavior of the ``PicklableLambda`` wrapper used under the spawn method."""

    def test_lambda_returns_a_picklable_wrapper_on_mac(self):
        wrapped = Lambda(lambda x: x)
        assert isinstance(wrapped, PicklableLambda) is IS_RUNNING_ON_MAC

    def test_wrapper_copies_and_restores_function_metadata(self):
        original = PicklableLambda(lambda x: x)
        assert original.__name__ == "<lambda>"
        restored = dill.loads(dill.dumps(original))
        assert restored.__name__ == "<lambda>"
        assert restored(7) == 7
