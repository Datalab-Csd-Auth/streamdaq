import dill


class Lambda:
    """
    A wrapper class to make lambda functions picklable using dill.
    This solves pickling errors when Pathway or other distributed systems
    attempt to serialize an anonymous function.
    """

    def __init__(self, func):
        self.func = func
        self.__name__ = getattr(func, "__name__", "<lambda>")
        self.__qualname__ = getattr(func, "__qualname__", "<lambda>")
        self.__module__ = getattr(func, "__module__", "")

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __getstate__(self):
        return dill.dumps(self.func)

    def __setstate__(self, state):
        self.func = dill.loads(state)
        self.__name__ = getattr(self.func, "__name__", "<lambda>")
        self.__qualname__ = getattr(self.func, "__qualname__", "<lambda>")
        self.__module__ = getattr(self.func, "__module__", "")
