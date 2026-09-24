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


@pytest.fixture(autouse=True)
def isolate_assessment_registry():
    """
    Snapshot ``ASSESSMENT_REGISTRY`` and restore it in place after every test, so that
    tests that register custom assessments never leak entries into one another.
    """
    import streamdaq.assessments.registry as registry

    snapshot = dict(registry.ASSESSMENT_REGISTRY)
    yield registry.ASSESSMENT_REGISTRY
    registry.ASSESSMENT_REGISTRY.clear()
    registry.ASSESSMENT_REGISTRY.update(snapshot)


@pytest.fixture(autouse=True)
def isolate_source_registry():
    """
    Snapshot ``SOURCE_REGISTRY`` and restore it in place after every test, so that tests that
    register custom sources never leak entries into one another.
    """
    import streamdaq.api.registries as registries

    snapshot = dict(registries.SOURCE_REGISTRY)
    yield registries.SOURCE_REGISTRY
    registries.SOURCE_REGISTRY.clear()
    registries.SOURCE_REGISTRY.update(snapshot)
