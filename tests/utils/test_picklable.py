"""Tests for the ``Lambda`` picklable wrapper.

The wrapper exists so that lambdas and other non-standard callables survive
``pickle`` when a task is dispatched to a separate ``multiprocessing`` process
(spawn start method). The critical behavior is therefore the ``__getstate__`` /
``__setstate__`` round-trip via ``dill``.
"""

import pickle

from streamdaq.utils.picklable import Lambda


def _module_level_add(a, b):
    return a + b


class TestLambdaCall:
    def test_wraps_and_calls_lambda(self):
        wrapped = Lambda(lambda x: x * 2)
        assert wrapped(21) == 42

    def test_forwards_args_and_kwargs(self):
        wrapped = Lambda(lambda a, b, c=0: a + b + c)
        assert wrapped(1, 2, c=3) == 6


class TestLambdaMetadata:
    def test_copies_named_function_metadata(self):
        wrapped = Lambda(_module_level_add)
        assert wrapped.__name__ == "_module_level_add"
        assert wrapped.__module__ == __name__


class TestLambdaPickling:
    """The whole reason this class exists: surviving pickle across processes."""

    def test_lambda_round_trips_through_pickle(self):
        wrapped = Lambda(lambda x: x + 100)
        restored = pickle.loads(pickle.dumps(wrapped))
        assert restored(1) == 101

    def test_closure_is_preserved(self):
        factor = 7
        wrapped = Lambda(lambda x: x * factor)
        restored = pickle.loads(pickle.dumps(wrapped))
        assert restored(3) == 21

    def test_metadata_restored_after_unpickle(self):
        wrapped = Lambda(_module_level_add)
        restored = pickle.loads(pickle.dumps(wrapped))
        assert restored.__name__ == "_module_level_add"
        assert restored(2, 5) == 7
