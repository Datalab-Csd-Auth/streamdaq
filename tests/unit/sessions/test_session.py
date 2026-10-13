import multiprocessing as mp
import time
from pathlib import Path
from unittest.mock import MagicMock

from streamdaq.api.models import (
    InputConfig,
    InstantCheckConfig,
    OutputConfig,
    TaskConfig,
    TaskStatus,
)
from streamdaq.sessions.base import Session
from streamdaq.storage.watermark_store import WatermarkStore
from streamdaq.tasks.base import Task


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
    store = session.get_tasks_store()
    for config in configs:
        store[config.name] = config


class TestSessionClearAndRestore:
    def test_keep_preserves_the_store_across_sessions(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        writer = Session(clear=True)
        _write_configs(writer, _persisted_config("t", TaskStatus.RUNNING))
        writer.db.close()

        reader = Session(clear=False).get_tasks_store()
        assert [name for name, _ in reader.items()] == ["t"]

    def test_clear_wipes_the_store(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        writer = Session(clear=True)
        _write_configs(writer, _persisted_config("t", TaskStatus.RUNNING))
        writer.db.close()

        reader = Session(clear=True).get_tasks_store()
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

        assert sorted(session.tasks) == ["running_task"]

    def test_restore_is_idempotent(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session(clear=True)
        _write_configs(session, _persisted_config("running_task", TaskStatus.RUNNING))

        session.restore_tasks()
        session.restore_tasks()

        assert list(session.tasks) == ["running_task"]


class TestSessionGracefullyKill:
    def test_kills_every_task_with_the_given_timeout(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)  # confine the session's on-disk store to a temp dir
        session = Session()
        session.tasks = {"a": MagicMock(), "b": MagicMock()}

        session.gracefully_kill(timeout_seconds=7)

        for task in session.tasks.values():
            task.gracefully_kill.assert_called_once_with(7)

    def test_no_tasks_is_a_noop(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session()

        session.gracefully_kill(timeout_seconds=7)  # must not raise


def _idle_worker() -> None:
    """Stand-in worker body: stay alive until terminated so swaps have a real child to kill."""
    time.sleep(300)


def _config(name: str = "t") -> TaskConfig:
    return TaskConfig(
        name=name,
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


class TestSessionBlueGreenSwap:
    """register_task / hotswap_task drive real worker processes and the sidecar metadata store.

    ``_start_pw_process`` is replaced so each task attaches a real, long-lived child process (a
    genuine PID to kill) without constructing the full Pathway pipeline; ``build_task`` is
    replaced with a lightweight Task so no registries/engine are exercised. The swap semantics,
    process coexistence, and metadata are the real objects under test.
    """

    def _patch_real_workers(self, monkeypatch) -> list:
        spawned: list = []
        ctx = mp.get_context("spawn")

        def fake_start(task_self):
            task_self._pw_process = ctx.Process(target=_idle_worker, daemon=True)
            task_self._pw_process.start()
            spawned.append(task_self._pw_process)

        monkeypatch.setattr(Task, "_start_pw_process", fake_start)
        monkeypatch.setattr(
            "streamdaq.sessions.base.build_task",
            lambda config, **kwargs: Task(
                input=lambda **_: None, output=lambda *_a, **_k: None, name=config.name
            ),
        )
        return spawned

    def _kill_spawned(self, spawned: list) -> None:
        for process in spawned:
            if process.is_alive():
                process.kill()
                process.join()

    def test_register_task_persists_config_and_initial_metadata(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        spawned = self._patch_real_workers(monkeypatch)
        session = Session(clear=True)
        try:
            session.register_task(_config("t"))

            assert "t" in session.tasks
            assert session.get_tasks_store()["t"].status == TaskStatus.RUNNING
            metadata = session.get_metadata_store()["t"]
            assert metadata.version == 1
            assert metadata.started_at > 0
        finally:
            self._kill_spawned(spawned)

    def test_hotswap_starts_new_then_kills_old_and_bumps_version(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        spawned = self._patch_real_workers(monkeypatch)
        session = Session(clear=True)
        try:
            session.register_task(_config("t"))
            old_task = session.tasks["t"]
            old_started_at = session.get_metadata_store()["t"].started_at

            session.hotswap_task(_config("t"))
            new_task = session.tasks["t"]
            metadata = session.get_metadata_store()["t"]

            assert new_task is not old_task
            assert new_task._pw_process.pid != old_task._pw_process.pid
            assert new_task._pw_process.is_alive()
            assert not old_task._pw_process.is_alive()
            assert metadata.version == 2
            assert metadata.started_at >= old_started_at
        finally:
            self._kill_spawned(spawned)

    def test_hotswap_failure_leaves_old_task_and_storage_untouched(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        spawned = self._patch_real_workers(monkeypatch)
        session = Session(clear=True)
        try:
            session.register_task(_config("t"))
            old_task = session.tasks["t"]

            def failing_start(task_self):
                raise RuntimeError("spawn failed")

            monkeypatch.setattr(Task, "_start_pw_process", failing_start)

            try:
                session.hotswap_task(_config("t"))
            except RuntimeError as error:
                assert str(error) == "spawn failed"
            else:
                raise AssertionError("hotswap_task should have raised")

            assert session.tasks["t"] is old_task
            assert old_task._pw_process.is_alive()
            assert session.get_metadata_store()["t"].version == 1
        finally:
            self._kill_spawned(spawned)


class TestSessionWatermarkCleanup:
    def test_delete_watermark_store_removes_the_task_directory(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session(clear=True)

        watermark_path = session._get_watermark_path("t")
        store = WatermarkStore(watermark_path)
        store.advance_window_to(1000)
        store.close()
        assert Path(watermark_path).exists()

        session.delete_watermark_store("t")

        assert not Path(watermark_path).exists()

    def test_delete_watermark_store_is_a_noop_when_absent(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        session = Session(clear=True)

        session.delete_watermark_store("never_created")
