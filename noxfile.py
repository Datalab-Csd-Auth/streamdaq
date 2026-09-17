import nox
from nox.sessions import Session

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["tests"]

PYTHON_VERSIONS = ["3.11", "3.12", "3.13"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session: Session) -> None:
    """Run the test suite with pytest and coverage."""
    session.install(".[test]")
    session.run("pytest")


@nox.session(name="integration-tests", python=PYTHON_VERSIONS)
def integration_tests(session: Session) -> None:
    """Run the end-to-end API integration tests (opt-in; excluded from the default run)."""
    session.install(".[test]")
    session.run(
        "pytest",
        "integration-tests",
        "-o",
        "addopts=",
        "-o",
        "testpaths=integration-tests",
        env={"PYTHONPATH": "integration-tests"},
    )
