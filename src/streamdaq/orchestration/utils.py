import importlib.util
from multiprocessing import Process
from pathlib import Path


def gracefully_kill(process: Process, timeout_seconds: int):
    if not process.is_alive():
        return

    process.terminate()
    process.join(timeout=timeout_seconds)
    if process.is_alive():  # pragma: no cover (cannot be reliably tested)
        process.kill()
        process.join()


def load_additional_files(path_str: str) -> None:
    path = Path(path_str).resolve()
    if not path.exists():
        raise FileNotFoundError(
            f"Cannot load additional streamdaq files: '{path_str}' does not exist."
        )

    files = list(path.glob("*.py")) if path.is_dir() else [path]
    for file_path in files:
        if file_path.name.startswith("_"):
            print(f"Skipping {file_path.name} because it starts with '_'.")
            continue

        module_name = f"streamdaq_user_files_{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)

        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
