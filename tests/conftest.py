import pytest


@pytest.fixture(autouse=True)
def isolate_registry():
    """
    Snapshot ``MEASURE_REGISTRY`` and restore it in place after every test, so that
    tests that register custom measures never leak entries into one another.
    """
    from streamdaq.measures.registry import MEASURE_REGISTRY

    snapshot = dict(MEASURE_REGISTRY)
    yield MEASURE_REGISTRY
    MEASURE_REGISTRY.clear()
    MEASURE_REGISTRY.update(snapshot)


@pytest.fixture(autouse=True)
def isolate_assessment_registry():
    """
    Snapshot ``ASSESSMENT_REGISTRY`` and restore it in place after every test, so that
    tests that register custom assessments never leak entries into one another.
    """
    from streamdaq.assessments.registry import ASSESSMENT_REGISTRY

    snapshot = dict(ASSESSMENT_REGISTRY)
    yield ASSESSMENT_REGISTRY
    ASSESSMENT_REGISTRY.clear()
    ASSESSMENT_REGISTRY.update(snapshot)


@pytest.fixture(autouse=True)
def isolate_source_registry():
    """
    Snapshot ``SOURCE_REGISTRY`` and restore it in place after every test, so that tests that
    register custom sources never leak entries into one another.
    """
    from streamdaq.io.sources.registry import SOURCE_REGISTRY

    snapshot = dict(SOURCE_REGISTRY)
    yield SOURCE_REGISTRY
    SOURCE_REGISTRY.clear()
    SOURCE_REGISTRY.update(snapshot)
