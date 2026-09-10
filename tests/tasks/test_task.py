from unittest.mock import MagicMock, patch

from streamdaq.tasks.base import Task


def _task() -> Task:
    return Task(input=lambda: None, output=lambda *a, **k: None, name="t")


class TestTaskGracefullyKill:
    def test_no_op_when_process_never_started(self):
        task = _task()
        with patch("streamdaq.tasks.base.gracefully_kill") as mock_kill:
            task.gracefully_kill(timeout_seconds=5)
        mock_kill.assert_not_called()

    def test_delegates_to_orchestration_kill_when_process_exists(self):
        task = _task()
        task._pw_process = MagicMock()
        with patch("streamdaq.tasks.base.gracefully_kill") as mock_kill:
            task.gracefully_kill(timeout_seconds=5)
        mock_kill.assert_called_once_with(task._pw_process, 5)
