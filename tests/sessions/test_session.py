from unittest.mock import MagicMock

from streamdaq.sessions.base import Session


class TestSessionGracefullyKill:
    def test_kills_every_task_with_the_given_timeout(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)  # confine the session's on-disk store to a temp dir
        session = Session()
        session.tasks = [MagicMock(), MagicMock()]

        session.gracefully_kill(timeout_seconds=7)

        for task in session.tasks:
            task.gracefully_kill.assert_called_once_with(7)

    def test_no_tasks_is_a_noop(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session()

        session.gracefully_kill(timeout_seconds=7)  # must not raise
