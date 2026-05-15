from streamdaq.utils.correlation_method import CorrelationMethod, correlation_method_to_function_map


class TestCorrelationMethodMap:
    def test_all_enum_members_in_map(self):
        """If a new CorrelationMethod is added to the enum, it must also be added to the map."""
        for member in CorrelationMethod:
            assert member in correlation_method_to_function_map, (
                f"CorrelationMethod.{member.name} does not have a computation function. "
                f"Add it to the map in utils/correlation_method.py."
            )

    def test_all_map_keys_are_valid_enum_members(self):
        for key in correlation_method_to_function_map:
            assert key in CorrelationMethod

    def test_enum_values_are_lowercase(self):
        for member in CorrelationMethod:
            assert member.value == member.name.lower()

    def test_functions_are_callable(self):
        for fn in correlation_method_to_function_map.values():
            assert callable(fn)

    def test_functions_return_float(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        for method, fn in correlation_method_to_function_map.items():
            result = fn(x, y)
            assert isinstance(result, float), f"{method} returned {type(result)}, expected float"
