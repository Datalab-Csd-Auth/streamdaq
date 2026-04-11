# Development Guide

Welcome! Thank you for wanting to contribute to `streamdaq`. This guide provides the commands to set up your environment and run our quality checks locally.

## Prerequisites
* Python 3.11, 3.12, or 3.13
* [uv](https://github.com/astral-sh/uv) installed (see https://docs.astral.sh/uv/getting-started/installation/ for one-liner installation based on OS)
* [hatch](https://hatch.pypa.io/) installed globally (`uv tool install hatch`)

## Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Datalab-Csd-Auth/streamdaq.git
   cd streamdaq
   ```

2. **Install the project and development dependencies:**
   Use `uv` to create a virtual environment and install everything needed:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```
> [!TIP]
> You can verify installation with `uv pip show streamdaq`

3. **Install Pre-commit hooks:**
   ```bash
   pre-commit install
   # expected output: pre-commit installed at .git/hooks/pre-commit
   ```

🎉 Congrats, you are are officially ready to start streamdaq-ing in dev mode!


## Local Development Commands

Before opening a Pull Request, please ensure your code passes our quality gates.
> [!WARNING]
> Streamdaq uses automated quality guardrails as GitHub actions before merging any code. The following commands can help you quickly check whether your to-contribute code meets these guardrails, without you having to deploy and wait for the build to finish. We strongly advise to use them often while you are developing and not just once when you are done. This way you can avoid surprises and significantly speed up development time, while maintaining the streamdaq's quality bar high.

### Formatting & Linting (Ruff & Mypy)
Pre-commit handles this automatically on `git commit`, but you can run the checks manually at any time:

* **Run all pre-commit hooks on all files (ruff + Mypy):**
  ```bash
  pre-commit run --all-files
  ```
* **Run ONLY Ruff (Linting & Formatting):**
  ```bash
  ruff check . --fix && ruff format .
  ```
* **Run ONLY Mypy (Type Checking):**
  ```bash
  mypy src/
  ```

### Testing (Pytest & Nox)
We use `pytest` for unit tests and `nox` to test across multiple Python versions. Our CI requires 100% passing tests and a minimum of 90% line coverage.

* **Run tests quickly in your current environment:**
  ```bash
  pytest
  ```
* **Run the full test matrix (Python 3.11, 3.12, 3.13):**
  ```bash
  nox
  ```

### Documentation (MkDocs)
If you are adding a feature, please update the documentation or Jupyter Notebooks.

* **Serve the documentation locally (auto-reloads on save):**
  ```bash
  mkdocs serve --livereload
  ```

### Versioning & Building (Hatch)
We use Hatch to manage the project version and build the distribution files.

* **Check the current version:**
  ```bash
  hatch version
  ```
* **Bump the version (e.g., patch, minor, or major):**
  ```bash
  hatch version patch  # Changes 0.1.0 to 0.1.1
  hatch version minor  # Changes 0.1.1 to 0.2.0
  hatch version major  # Changes 0.2.0 to 1.0.0
  ```
* **Build the package locally (creates `dist/` directory with wheel and sdist):**
  ```bash
  hatch build
  ```
