from unittest.mock import MagicMock

from streamdaq.api.models import (
    InputConfig,
    InstantCheckConfig,
    OutputConfig,
    TaskConfig,
    TaskStatus,
)
from streamdaq.sessions.base import Session
from streamdaq.storage.lmdb_store import NamespaceStore


def _persisted_config(name: str, status: TaskStatus) -> TaskConfig:
    return TaskConfig(
        name=name,
        status=status,
        input=InputConfig(type="csv", params={"path": "/tmp/data.csv"}),
        output=OutputConfig(type="jsonlines", params={"filename": "out.jsonl"}),
        instant_checks=[
            InstantCheckConfig(
                name="age_in_range",
                check_class="InRange",
                params={"column": "age", "low": 0, "high": 120},
            )
        ],
    )


def _write_configs(session: Session, *configs: TaskConfig) -> None:
    store = NamespaceStore(session.db, "api_tasks", value_type=TaskConfig)
    for config in configs:
        store[config.name] = config


class TestSessionClearAndRestore:
    def test_keep_preserves_the_store_across_sessions(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        writer = Session(clear=True)
        _write_configs(writer, _persisted_config("t", TaskStatus.RUNNING))
        writer.db.close()

        reader = NamespaceStore(Session(clear=False).db, "api_tasks", value_type=TaskConfig)
        assert [name for name, _ in reader.items()] == ["t"]

    def test_clear_wipes_the_store(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        writer = Session(clear=True)
        _write_configs(writer, _persisted_config("t", TaskStatus.RUNNING))
        writer.db.close()

        reader = NamespaceStore(Session(clear=True).db, "api_tasks", value_type=TaskConfig)
        assert list(reader.items()) == []

    def test_restore_resumes_only_running_tasks(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session(clear=True)
        _write_configs(
            session,
            _persisted_config("running_task", TaskStatus.RUNNING),
            _persisted_config("finished_task", TaskStatus.FINISHED),
        )

        session.restore_tasks()

        assert sorted(task.name for task in session.tasks) == ["running_task"]

    def test_restore_is_idempotent(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session(clear=True)
        _write_configs(session, _persisted_config("running_task", TaskStatus.RUNNING))

        session.restore_tasks()
        session.restore_tasks()

        assert [task.name for task in session.tasks] == ["running_task"]


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
