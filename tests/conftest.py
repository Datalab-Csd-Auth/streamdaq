import pytest


@pytest.fixture(autouse=True)
def isolate_registry():
    """
    Snapshot ``MEASURE_REGISTRY`` and restore it in place after every test, so that
    tests that register custom measures never leak entries into one another.
    """
    import streamdaq.api.registries as registries

    snapshot = dict(registries.MEASURE_REGISTRY)
    yield registries.MEASURE_REGISTRY
    registries.MEASURE_REGISTRY.clear()
    registries.MEASURE_REGISTRY.update(snapshot)
