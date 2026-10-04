import time
from unittest.mock import MagicMock

import pytest
import uvicorn

from streamdaq.api import server
from streamdaq.api.server import _ThreadedUvicornServer, serve
from streamdaq.api.utils import DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS
from streamdaq.sessions.base import Session


async def _dummy_asgi_app(scope, receive, send): ...


def _make_config():
    return uvicorn.Config(_dummy_asgi_app, host="127.0.0.1", port=0)


class TestThreadedUvicornServer:
    def test_does_not_override_signal_handlers(self):
        # Relies on uvicorn's own no-op-off-main-thread behavior; must not install its own
        assert "install_signal_handlers" not in _ThreadedUvicornServer.__dict__

    def test_start_in_thread_returns_running_thread_once_started(self):
        instance = _ThreadedUvicornServer(_make_config())

        def fake_run():
            instance.started = True
            while not instance.should_exit:
                time.sleep(0.01)

        instance.run = fake_run  # type: ignore[method-assign]

        thread = instance.start_in_thread()
        try:
            assert thread.is_alive()
            assert thread.daemon
            assert instance.started
        finally:
            instance.should_exit = True
            thread.join()
        assert not thread.is_alive()

    def test_start_in_thread_raises_if_thread_dies_before_startup(self):
        instance = _ThreadedUvicornServer(_make_config())

        def fake_run():
            return  # exits immediately without ever setting `started`

        instance.run = fake_run  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="before startup completed"):
            instance.start_in_thread()


class TestServe:
    def _patch_server(self, monkeypatch, thread):
        instance = MagicMock()
        instance.should_exit = False
        instance.start_in_thread.return_value = thread
        monkeypatch.setattr(server, "_ThreadedUvicornServer", MagicMock(return_value=instance))
        return instance

    def test_mounts_session_and_supervises_until_thread_exits(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session()
        thread = MagicMock()
        thread.is_alive.side_effect = [True, False]  # alive once, then the server stops
        instance = self._patch_server(monkeypatch, thread)

        captured = {}
        real_api = server.StreamdaqApi

        def spy_api(mounted_session):
            api = real_api(mounted_session)
            captured["session"] = api.app.state.session
            return api

        monkeypatch.setattr(server, "StreamdaqApi", spy_api)

        serve(session, host="127.0.0.1", port=8123)

        assert captured["session"] is session  # the served Api owns the given session
        instance.start_in_thread.assert_called_once()
        thread.join.assert_called_once_with(server._SERVER_SUPERVISE_INTERVAL_SECONDS)

    def test_forwards_host_port_and_kwargs_to_uvicorn_config(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session()
        thread = MagicMock()
        thread.is_alive.return_value = False
        self._patch_server(monkeypatch, thread)

        captured = {}

        def fake_config(app, **kwargs):
            captured["app"] = app
            captured.update(kwargs)
            return MagicMock()

        monkeypatch.setattr(server.uvicorn, "Config", fake_config)

        serve(session, host="0.0.0.0", port=9999, log_level="warning")

        assert captured["host"] == "0.0.0.0"
        assert captured["port"] == 9999
        assert captured["log_level"] == "warning"

    def test_keyboard_interrupt_triggers_graceful_shutdown(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session()
        thread = MagicMock()
        thread.is_alive.return_value = True
        join_calls = []

        def join_side_effect(*args):
            join_calls.append(args)
            if len(join_calls) == 1:  # Ctrl+C lands while supervising
                raise KeyboardInterrupt

        thread.join.side_effect = join_side_effect
        instance = self._patch_server(monkeypatch, thread)

        serve(session, host="127.0.0.1", port=8080)

        assert instance.should_exit is True
        # first join is the timed supervise wait, second is the unbounded shutdown wait
        assert join_calls == [(server._SERVER_SUPERVISE_INTERVAL_SECONDS,), ()]

    def test_safety_net_kills_tasks_still_running_after_shutdown(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session()
        live_task = MagicMock()
        live_task._pw_process.is_alive.return_value = True
        session.tasks = [live_task]
        thread = MagicMock()
        thread.is_alive.return_value = False
        self._patch_server(monkeypatch, thread)

        serve(session, host="127.0.0.1", port=8080)

        live_task.gracefully_kill.assert_called_once_with(DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS)

    def test_safety_net_is_skipped_when_no_tasks_are_running(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session()
        session.gracefully_kill = MagicMock()  # type: ignore[method-assign]
        thread = MagicMock()
        thread.is_alive.return_value = False
        self._patch_server(monkeypatch, thread)

        serve(session, host="127.0.0.1", port=8080)

        session.gracefully_kill.assert_not_called()

    def test_tasks_are_killed_when_server_fails_to_start(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session()
        live_task = MagicMock()
        live_task._pw_process.is_alive.return_value = True
        session.tasks = [live_task]
        instance = MagicMock()
        instance.start_in_thread.side_effect = RuntimeError("port already in use")
        monkeypatch.setattr(server, "_ThreadedUvicornServer", MagicMock(return_value=instance))

        with pytest.raises(RuntimeError, match="port already in use"):
            serve(session, host="127.0.0.1", port=8080)

        live_task.gracefully_kill.assert_called_once_with(DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS)
