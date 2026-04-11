import nox
from nox.sessions import Session

# Use uv for blazing fast virtual environment creation
nox.options.default_venv_backend = "uv"


@nox.session(python=["3.11", "3.12"])
def tests(session: Session) -> None:
    """Run the test suite with pytest and coverage."""
    # Install the package itself along with test dependencies
    session.install(".[test]")
    session.run("pytest")
