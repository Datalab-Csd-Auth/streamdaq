from multiprocessing import Process


def gracefully_kill(process: Process, timeout_seconds: int):
    if not process.is_alive():
        return

    process.terminate()
    process.join(timeout=timeout_seconds)
    if process.is_alive():  # pragma: no cover (cannot be reliably tested)
        process.kill()
        process.join()
