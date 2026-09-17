"""Shared fixtures/hooks for the integration test suite."""

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Record each phase's outcome on the test item so fixtures can react to failures."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"report_{report.when}", report)
