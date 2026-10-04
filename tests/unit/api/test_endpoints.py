from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from streamdaq.api.routes import get_session
from unit.api.conftest import app, make_mock_session, test_session

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_tasks_store():
    # Setup: clear tasks before test
    test_session.tasks_store().clear()
    yield
    # Teardown: clear tasks after test
    test_session.tasks_store().clear()
    app.dependency_overrides.clear()


def test_create_task_invalid_measure_in_window_checks():
    payload = {
        "name": "My Task",
        "input": {"type": "kafka", "params": {}},
        "output": {"type": "jsonlines", "params": {}},
        "window_checks_config": {
            "window": {"type": "sliding", "params": {}},
            "checks": [
                {
                    "name": "test_check",
                    "measure": {
                        "type": "InRangeCount",
                        "params": {"column": "age"},
                    },  # missing low/high
                    "must_be": ">0",
                }
            ],
        },
    }
    response = client.post("/api/v1/bulk_create", json=[payload])
    assert response.status_code == 400
    assert "Invalid params for InRangeCount" in response.json()["detail"]


def test_create_task_invalid_instant_check():
    payload = {
        "name": "My Task 2",
        "input": {"type": "kafka", "params": {}},
        "output": {"type": "jsonlines", "params": {}},
        "instant_checks": [
            {
                "name": "test_instant",
                "check_class": "InRange",
                "params": {"column": "age"},  # missing low/high
            }
        ],
    }
    response = client.post("/api/v1/bulk_create", json=[payload])
    assert response.status_code == 400
    assert "Invalid params for InRange" in response.json()["detail"]


@patch("streamdaq.api.routes.build_task")
def test_create_task_valid(mock_build_task):
    mock_session = make_mock_session()
    app.dependency_overrides[get_session] = lambda: mock_session
    mock_task = MagicMock()
    mock_build_task.return_value = mock_task

    io_skeleton = {
        "input": {"type": "kafka", "params": {}},
        "output": {"type": "jsonlines", "params": {}},
    }
    window_checks = {
        "windowby_column": "age",
        "window_checks_config": {
            "window": {"type": "sliding", "params": {}},
            "checks": [
                {
                    "name": "mean_ok",
                    "measure": {"type": "Mean", "params": {"column": "age"}},
                    "must_be": "[0, 100]",
                }
            ],
        },
    }
    instant_checks = {
        "instant_checks": [
            {
                "name": "test_instant",
                "check_class": "InRange",
                "params": {"column": "age", "low": 0, "high": 100},
            }
        ]
    }

    valid_payload_only_window_checks = {
        "name": "Window Only",
        "wait_for_late": 5,
        **io_skeleton,
        **window_checks,
    }
    valid_payload_only_instant_checks = {
        "name": "Instant Only",
        "wait_for_late": 5,
        **io_skeleton,
        **instant_checks,
    }
    valid_payload_window_instant_checks = {
        "name": "Window and Instant",
        **io_skeleton,
        **window_checks,
        **instant_checks,
    }

    response = client.post(
        "/api/v1/bulk_create",
        json=[
            valid_payload_only_window_checks,
            valid_payload_only_instant_checks,
            valid_payload_window_instant_checks,
        ],
    )
    assert response.status_code == 201
    assert response.json()["task_ids"] == ["Window Only", "Instant Only", "Window and Instant"]
    assert "Window Only" in test_session.tasks_store()
    assert "Instant Only" in test_session.tasks_store()
    assert "Window and Instant" in test_session.tasks_store()

    assert mock_build_task.call_count == 3
    assert mock_session.add_tasks.call_count == 3
    assert mock_task._start_pw_process.call_count == 3
