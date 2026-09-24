import enum


class Py312EnumMeta(enum.EnumMeta):
    """
    The Py312EnumMeta is a metaclass that allows using the `in` operator,
    e.g., `assert "native" in StreamdaqDataFormat == True`.
    The default behaviour in Python 3.11 is to raise a TypeError.
    This class aligns with the default behaviour in Python 3.12+, which was
    changed to return True/False:
    https://docs.python.org/3/library/enum.html#enum.EnumType.__contains__.

    Usage:
    ```
        from enum import Enum
        from ...common import Py312EnumMeta

        class MyEnum(Enum, metaclass=Py312EnumMeta):
            FIRST = "first"
            SECOND = "second"

        class AnotherEnum(Enum):
            FIRST = "first"
            SECOND = "second"

        print("first" in MyEnum)  # prints True in Python 3.11+
        print("third" in MyEnum)  # prints False in Python 3.11+

        print("first" in AnotherEnum)  # raises TypeError in Python 3.11, prints True in 3.12+
    ```
    """

    def __contains__(self, other):
        try:
            self(other)
        except ValueError:
            return False
        else:
            return True
