from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import streamdaq.api.routes as routes
from streamdaq.api.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_tasks_store():
    # Setup: clear tasks before test
    routes._TASKS_STORE.clear()
    yield
    # Teardown: clear tasks after test
    routes._TASKS_STORE.clear()


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
    response = client.post("/api/v1/bulk_create", json=payload)
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
    response = client.post("/api/v1/bulk_create", json=payload)
    assert response.status_code == 400
    assert "Invalid params for InRange" in response.json()["detail"]


@patch("streamdaq.api.routes.build_task")
@patch("streamdaq.api.routes._get_session")
def test_create_task_valid(mock_get_session, mock_build_task):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_task = MagicMock()
    mock_build_task.return_value = mock_task

    payload = {
        "name": "Valid Task",
        "windowby_column": "age",
        "window_checks_config": {"window": {"type": "sliding", "params": {}}, "checks": []},
        "input": {"type": "kafka", "params": {}},
        "output": {"type": "jsonlines", "params": {}},
        "instant_checks": [
            {
                "name": "test_instant",
                "check_class": "InRange",
                "params": {"column": "age", "low": 0, "high": 100},
            }
        ],
    }
    response = client.post("/api/v1/bulk_create", json=payload)
    assert response.status_code == 201
    assert response.json()["task_id"] == "Valid Task"
    assert "Valid Task" in routes._TASKS_STORE

    mock_build_task.assert_called_once()
    mock_session.add_tasks.assert_called_once_with(mock_task)
    mock_task._start_pw_process.assert_called_once()
