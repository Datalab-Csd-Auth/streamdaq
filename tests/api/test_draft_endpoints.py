"""Tests for the dynamic draft task builder API endpoints.

Covers:
- Creating draft tasks (POST /api/v1/tasks/{task_id})
- Setting input/output configs (POST /api/v1/tasks/{task_id}/input)
- Adding/removing instant checks and window checks
- Starting a draft task (POST /start)
- Immutability checks when not DRAFT
- Error handling (404, 400, 422, 503)
- Full incremental build flow
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import streamdaq.api.routes as routes
from streamdaq.api.app import app

client = TestClient(app)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_tasks_store():
    """Ensure a clean task store for every test."""
    routes._TASKS_STORE.clear()
    yield
    routes._TASKS_STORE.clear()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _create_draft(
    task_id: str = "test-task", windowby_column: str = None, window_type: str = None
) -> dict:
    """Create a draft task and return the response."""
    payload = {"task_name": task_id}
    if windowby_column:
        payload["windowby_column"] = windowby_column
    if window_type:
        payload["window_type"] = window_type
    resp = client.post(f"/api/v1/tasks/{task_id}/init", json=payload)
    return resp


def _sample_input() -> dict:
    return {"type": "kafka", "params": {}}


def _sample_output() -> dict:
    return {"type": "jsonlines", "params": {}}


def _sample_instant_check(name: str = "range_check") -> dict:
    return {
        "name": name,
        "check_class": "InRange",
        "params": {"column": "temperature", "low": 0, "high": 100},
    }


def _sample_window_checks(
    check_names: list[str] | None = None,
    window_type: str = "sliding",
) -> dict:
    if check_names is None:
        check_names = ["mean_check"]
    return {
        "window": {"type": window_type, "params": {}},
        "checks": [
            {
                "name": cn,
                "measure": {"type": "Mean", "params": {"column": "value"}},
                "must_be": ">=0",
            }
            for cn in check_names
        ],
    }


# ─── 1. test_create_draft ────────────────────────────────────────────────────


def test_create_draft():
    """POST /tasks/{task_id} → 201, returns task_id, stored as draft."""
    resp = _create_draft("my-task")

    assert resp.status_code == 201
    body = resp.json()
    assert body["task_id"] == "my-task"
    assert "my-task" in routes._TASKS_STORE
    assert routes._TASKS_STORE["my-task"].status.value == "draft"


# ─── 2. test_update_draft ────────────────────────────────────────────────────


def test_update_draft():
    """POST /tasks/{task_id} twice on a draft allows updating fields."""
    _create_draft("my-task")
    resp = client.post(
        "/api/v1/tasks/my-task/init", json={"task_name": "new-name", "windowby_column": "col1"}
    )
    assert resp.status_code == 201

    config = routes._TASKS_STORE["my-task"]
    assert config.name == "new-name"
    assert config.windowby_column == "col1"


# ─── 3. test_set_input ──────────────────────────────────────────────────────


def test_set_input():
    """POST input on a draft → input config is stored."""
    _create_draft("inp-task")
    resp = client.post("/api/v1/tasks/inp-task/input", json=_sample_input())

    assert resp.status_code == 200
    config = routes._TASKS_STORE["inp-task"]
    assert config.input is not None
    assert config.input.type == "kafka"


# ─── 4. test_set_output ─────────────────────────────────────────────────────


def test_set_output():
    """POST output on a draft → output config is stored."""
    _create_draft("out-task")
    resp = client.post("/api/v1/tasks/out-task/output", json=_sample_output())

    assert resp.status_code == 200
    config = routes._TASKS_STORE["out-task"]
    assert config.output is not None
    assert config.output.type == "jsonlines"


# ─── 5. test_add_instant_check ──────────────────────────────────────────────


def test_add_instant_check():
    """POST instant-checks → check appears in config."""
    _create_draft("ic-task")
    resp = client.post(
        "/api/v1/tasks/ic-task/instant-checks",
        json=_sample_instant_check("temp_check"),
    )

    assert resp.status_code == 200
    config = routes._TASKS_STORE["ic-task"]
    assert len(config.instant_checks) == 1
    assert config.instant_checks[0].name == "temp_check"


# ─── 6. test_add_window_checks ──────────────────────────────────────────────


def test_add_window_checks():
    """POST window-checks → window_checks_config is set."""
    _create_draft("wc-task")
    resp = client.post(
        "/api/v1/tasks/wc-task/window-checks",
        json=_sample_window_checks(["wc1"]),
    )

    assert resp.status_code == 200
    config = routes._TASKS_STORE["wc-task"]
    assert config.window_checks_config is not None
    assert len(config.window_checks_config.checks) == 1
    assert config.window_checks_config.checks[0].name == "wc1"
    assert config.window_checks_config.window.type == "sliding"


# ─── 7. test_add_window_checks_appends ──────────────────────────────────────


def test_add_window_checks_appends():
    """Adding window checks twice → checks accumulate, window config is replaced."""
    _create_draft("wca-task")
    client.post(
        "/api/v1/tasks/wca-task/window-checks",
        json=_sample_window_checks(["first_check"], window_type="sliding"),
    )
    client.post(
        "/api/v1/tasks/wca-task/window-checks",
        json=_sample_window_checks(["second_check"], window_type="tumbling"),
    )

    config = routes._TASKS_STORE["wca-task"]
    wcc = config.window_checks_config
    assert wcc is not None
    check_names = [c.name for c in wcc.checks]
    assert "first_check" in check_names
    assert "second_check" in check_names
    assert len(wcc.checks) == 2
    assert wcc.window.type == "tumbling"


# ─── 8. test_remove_instant_check ───────────────────────────────────────────


def test_remove_instant_check():
    """Add an instant check, then DELETE it → check is gone."""
    _create_draft("ric-task")
    client.post(
        "/api/v1/tasks/ric-task/instant-checks",
        json=_sample_instant_check("to_remove"),
    )
    assert len(routes._TASKS_STORE["ric-task"].instant_checks) == 1

    resp = client.delete("/api/v1/tasks/ric-task/instant-checks/to_remove")
    assert resp.status_code == 200
    assert len(routes._TASKS_STORE["ric-task"].instant_checks) == 0


# ─── 9. test_remove_instant_check_not_found ─────────────────────────────────


def test_remove_instant_check_not_found():
    """DELETE a nonexistent instant check → 404."""
    _create_draft("ric404-task")
    resp = client.delete("/api/v1/tasks/ric404-task/instant-checks/ghost")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ─── 10. test_remove_window_check ───────────────────────────────────────────


def test_remove_window_check():
    """Add window checks, DELETE one by name → it's removed."""
    _create_draft("rwc-task")
    client.post(
        "/api/v1/tasks/rwc-task/window-checks",
        json=_sample_window_checks(["keep_me", "drop_me"]),
    )
    assert len(routes._TASKS_STORE["rwc-task"].window_checks_config.checks) == 2

    resp = client.delete("/api/v1/tasks/rwc-task/window-checks/drop_me")
    assert resp.status_code == 200

    remaining = routes._TASKS_STORE["rwc-task"].window_checks_config.checks
    assert len(remaining) == 1
    assert remaining[0].name == "keep_me"


# ─── 11. test_remove_window_check_not_found ─────────────────────────────────


def test_remove_window_check_not_found():
    """DELETE a nonexistent window check → 404."""
    _create_draft("rwc404-task")
    resp = client.delete("/api/v1/tasks/rwc404-task/window-checks/ghost")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ─── 12. test_start_task ────────────────────────────────────────────────────


@patch("streamdaq.api.routes.build_task")
@patch("streamdaq.api.routes._get_session")
def test_start_task(mock_get_session, mock_build_task):
    """Create draft → set input → set output → add check → start → 200, status=running."""
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_task = MagicMock()
    mock_build_task.return_value = mock_task

    _create_draft("start-task", windowby_column="col1", window_type="sliding")
    client.post("/api/v1/tasks/start-task/input", json=_sample_input())
    client.post("/api/v1/tasks/start-task/output", json=_sample_output())
    client.post(
        "/api/v1/tasks/start-task/instant-checks",
        json=_sample_instant_check(),
    )

    resp = client.post("/api/v1/tasks/start-task/start")
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "start-task"

    mock_build_task.assert_called_once()
    mock_session.add_tasks.assert_called_once_with(mock_task)
    mock_task._start_pw_process.assert_called_once()

    assert routes._TASKS_STORE["start-task"].status.value == "running"


# ─── 13. test_start_task_missing_input ──────────────────────────────────────


def test_start_task_missing_input():
    """Draft with output only → start fails with 422."""
    _create_draft("noinp-task", windowby_column="col1", window_type="sliding")
    client.post("/api/v1/tasks/noinp-task/output", json=_sample_output())
    client.post("/api/v1/tasks/noinp-task/instant-checks", json=_sample_instant_check())

    resp = client.post("/api/v1/tasks/noinp-task/start")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any("Input" in d for d in detail)


# ─── 14. test_start_task_missing_output ─────────────────────────────────────


def test_start_task_missing_output():
    """Draft with input only → start fails with 422."""
    _create_draft("noout-task", windowby_column="col1", window_type="sliding")
    client.post("/api/v1/tasks/noout-task/input", json=_sample_input())
    client.post("/api/v1/tasks/noout-task/instant-checks", json=_sample_instant_check())

    resp = client.post("/api/v1/tasks/noout-task/start")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert any("Output" in d for d in detail)


# ─── 15. test_start_task_no_session ─────────────────────────────────────────


@patch("streamdaq.api.routes._get_session", return_value=None)
def test_start_task_no_session(mock_get_session):
    """Draft with input+output but no active session → 503."""
    _create_draft("nosess-task", windowby_column="col1", window_type="sliding")
    client.post("/api/v1/tasks/nosess-task/input", json=_sample_input())
    client.post("/api/v1/tasks/nosess-task/output", json=_sample_output())
    client.post("/api/v1/tasks/nosess-task/instant-checks", json=_sample_instant_check())

    resp = client.post("/api/v1/tasks/nosess-task/start")
    assert resp.status_code == 503
    assert "session" in resp.json()["detail"].lower()


# ─── 16. test_modify_running_task_immutability ──────────────────────────────


@patch("streamdaq.api.routes.build_task")
@patch("streamdaq.api.routes._get_session")
def test_modify_running_task_immutability(mock_get_session, mock_build_task):
    """Start a task, then try to change immutable fields → 400."""
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_build_task.return_value = MagicMock()

    _create_draft("run-task", windowby_column="col1", window_type="sliding")
    client.post("/api/v1/tasks/run-task/input", json=_sample_input())
    client.post("/api/v1/tasks/run-task/output", json=_sample_output())
    client.post("/api/v1/tasks/run-task/instant-checks", json=_sample_instant_check())
    client.post("/api/v1/tasks/run-task/start")

    # Try to modify name
    resp = client.post("/api/v1/tasks/run-task/init", json={"task_name": "new_name"})
    assert resp.status_code == 400
    assert "immutable" in resp.json()["detail"].lower()

    # Try to modify windowby_column
    resp = client.post(
        "/api/v1/tasks/run-task/init", json={"task_name": "run-task", "windowby_column": "col2"}
    )
    assert resp.status_code == 400
    assert "immutable" in resp.json()["detail"].lower()


# ─── 17. test_set_input_not_found ───────────────────────────────────────────


def test_set_input_not_found():
    """POST input on a nonexistent task → 404."""
    resp = client.post("/api/v1/tasks/nonexistent/input", json=_sample_input())
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ─── 18. test_get_draft_shows_status ────────────────────────────────────────


def test_get_draft_shows_status():
    """GET /tasks/{id} on a draft → status is 'draft'."""
    _create_draft("status-task")
    resp = client.get("/api/v1/tasks/status-task")

    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


# ─── 19. test_delete_draft ─────────────────────────────────────────────────


def test_delete_draft():
    """DELETE /tasks/{id} on a draft → 204, task is removed from store."""
    _create_draft("del-task")
    assert "del-task" in routes._TASKS_STORE

    resp = client.delete("/api/v1/tasks/del-task")
    assert resp.status_code == 204
    assert "del-task" not in routes._TASKS_STORE


# ─── 20. test_full_incremental_flow ─────────────────────────────────────────


@patch("streamdaq.api.routes.build_task")
@patch("streamdaq.api.routes._get_session")
@patch("streamdaq.api.routes._handle_running_task")
def test_full_incremental_flow(mock_restart, mock_get_session, mock_build_task):
    """End-to-end: create → input → output → instant check → window checks → start."""
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_task = MagicMock()
    mock_build_task.return_value = mock_task

    # 1. Create draft
    resp = _create_draft("e2e-task", windowby_column="col1")
    assert resp.status_code == 201
    assert routes._TASKS_STORE["e2e-task"].status.value == "draft"

    # 2. Set input
    resp = client.post("/api/v1/tasks/e2e-task/input", json=_sample_input())
    assert resp.status_code == 200
    assert routes._TASKS_STORE["e2e-task"].input is not None

    # 3. Set output
    resp = client.post("/api/v1/tasks/e2e-task/output", json=_sample_output())
    assert resp.status_code == 200
    assert routes._TASKS_STORE["e2e-task"].output is not None

    # 4. Add instant check
    resp = client.post(
        "/api/v1/tasks/e2e-task/instant-checks",
        json=_sample_instant_check("e2e_instant"),
    )
    assert resp.status_code == 200
    assert len(routes._TASKS_STORE["e2e-task"].instant_checks) == 1

    # 5. Add window checks
    resp = client.post(
        "/api/v1/tasks/e2e-task/window-checks",
        json=_sample_window_checks(["e2e_wc"]),
    )
    assert resp.status_code == 200
    assert routes._TASKS_STORE["e2e-task"].window_checks_config is not None

    # 6. Start
    resp = client.post("/api/v1/tasks/e2e-task/start")
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "e2e-task"

    # 7. Restart placeholder trigger
    resp = client.post("/api/v1/tasks/e2e-task/input", json=_sample_input())
    assert resp.status_code == 200
    mock_restart.assert_called_with("e2e-task", routes._TASKS_STORE["e2e-task"])

    # Verify final state
    config = routes._TASKS_STORE["e2e-task"]
    assert config.status.value == "running"
    assert config.input.type == "kafka"
    assert config.output.type == "jsonlines"
    assert len(config.instant_checks) == 1
    assert config.instant_checks[0].name == "e2e_instant"
    assert len(config.window_checks_config.checks) == 1
    assert config.window_checks_config.checks[0].name == "e2e_wc"

    # Verify engine interactions
    mock_build_task.assert_called_once()
    mock_session.add_tasks.assert_called_once_with(mock_task)
    mock_task._start_pw_process.assert_called_once()
