import nox
from nox.sessions import Session

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["tests"]

PYTHON_VERSIONS = ["3.11", "3.12", "3.13"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session: Session) -> None:
    """Run the test suite with pytest and coverage."""
    unit_tests_path = "tests/unit"
    session.install(".[test]")
    session.run(
        "pytest",
        unit_tests_path,
        "-o",
        "addopts=",
        "-o",
        f"testpaths={unit_tests_path}",
        env={"PYTHONPATH": unit_tests_path},
    )


@nox.session(name="integration", python=PYTHON_VERSIONS)
def integration_tests(session: Session) -> None:
    """Run the integration tests (opt-in; excluded from the default run)."""
    integration_tests_path = "tests/integration"
    session.install(".[test]")
    session.run(
        "pytest",
        integration_tests_path,
        "-o",
        "addopts=",
        "-o",
        f"testpaths={integration_tests_path}",
        env={"PYTHONPATH": integration_tests_path},
    )
