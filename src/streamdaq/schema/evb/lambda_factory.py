from collections.abc import Callable
from typing import Any

from streamdaq.utils.picklable import Lambda


class LambdaFactory:
    @classmethod
    def get_nth_list_element(cls, n: int, dtype: type | None = None) -> Callable:
        if not dtype:
            return Lambda(lambda elements: elements[n])

        dtype_to_lambda: dict[type, Callable] = {
            bool: Lambda(lambda elements: elements[n].as_bool()),
            dict: Lambda(lambda elements: elements[n].as_dict()),
            float: Lambda(lambda elements: elements[n].as_float()),
            int: Lambda(lambda elements: elements[n].as_int()),
            list: Lambda(lambda elements: elements[n].as_list()),
            str: Lambda(lambda elements: elements[n].as_str()),
        }
        if dtype not in dtype_to_lambda:
            raise NotImplementedError(
                f"Can't construct a lambda with the provided {dtype=}. "
                f"Available dtypes: {dtype_to_lambda.keys()}."
            )
        return dtype_to_lambda[dtype]

    @classmethod
    def get_list_elements_from_n_to_end(cls, n: int, dtype: type | None = None) -> Callable:
        if not dtype:
            return Lambda(lambda elements: list(elements[n:]))

        dtype_to_lambda: dict[type, Callable] = {
            bool: Lambda(lambda element: element.as_bool()),
            dict: Lambda(lambda element: element.as_dict()),
            float: Lambda(lambda element: element.as_float()),
            int: Lambda(lambda element: element.as_int()),
            list: Lambda(lambda element: element.as_list()),
            str: Lambda(lambda element: element.as_str()),
        }
        if dtype not in dtype_to_lambda:
            raise NotImplementedError(
                f"Cannot construct a lambda to cast list elements from n to end into {dtype}. "
                f"Available dtypes: {dtype_to_lambda.keys()}."
            )
        converter_lambda = dtype_to_lambda[dtype]
        return Lambda(lambda elements: [converter_lambda(element) for element in elements[n:]])

    @classmethod
    def check_nth_list_element_equals_value(
        cls, n: int, value: Any, dtype: type | None = None
    ) -> Callable[[list], bool]:
        getter_lambda = cls.get_nth_list_element(n, dtype)
        return Lambda(lambda elements: getter_lambda(elements) == value)

    @classmethod
    def check_int_has_exact_nof_digits(cls, nof_digits: int) -> Callable:
        return Lambda(lambda int_value: len(str(int_value)) == nof_digits)
