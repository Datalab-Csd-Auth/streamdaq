import threading
import time

import uvicorn

from streamdaq.api.app import StreamdaqApi
from streamdaq.api.utils import DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS
from streamdaq.sessions.base import Session

_SERVER_STARTUP_POLL_SECONDS = 0.05
_SERVER_SUPERVISE_INTERVAL_SECONDS = 0.5


class _ThreadedUvicornServer(uvicorn.Server):
    """Runs uvicorn in a daemon thread so the caller keeps the main thread free to supervise."""

    def start_in_thread(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        while not self.started:
            if not thread.is_alive():
                raise RuntimeError("uvicorn server exited before startup completed")
            time.sleep(_SERVER_STARTUP_POLL_SECONDS)
        return thread


def serve(session: Session, host: str, port: int, **kwargs) -> None:
    """Serve a session over HTTP, keeping the terminal attached and tasks torn down on Ctrl+C.

    Resumes persisted tasks (unless the store was cleared), starts every task in its own process,
    mounts the session onto the API, and runs uvicorn on a background thread while the main thread
    supervises. Ctrl+C triggers uvicorn's lifespan shutdown, which gracefully kills the workers.
    """
    # Resume tasks persisted by a previous session unless the store was cleared
    if not session.clear:
        session.restore_tasks()

    # Start the already added tasks (if any)
    session.start()

    # Build the single API instance that owns this session and serve its app
    streamdaq_api = StreamdaqApi(session)

    config = uvicorn.Config(streamdaq_api.app, host=host, port=port, **kwargs)
    server = _ThreadedUvicornServer(config)
    thread: threading.Thread | None = None
    try:
        thread = server.start_in_thread()
        while thread.is_alive():
            thread.join(_SERVER_SUPERVISE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        # Let uvicorn run its lifespan shutdown, which tears the session down via on_shutdown
        server.should_exit = True
        if thread is not None:
            thread.join()
    finally:
        # Guarantee no orphaned worker processes even if the shutdown hook did not run
        if session._has_running_tasks():
            session.gracefully_kill(DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS)
