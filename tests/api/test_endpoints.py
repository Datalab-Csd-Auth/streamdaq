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
@patch("streamdaq.api.routes._get_session")
def test_create_task_valid(mock_get_session, mock_build_task):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    mock_task = MagicMock()
    mock_build_task.return_value = mock_task

    payload1 = {
        "name": "Valid Task 1",
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

    payload2 = {
        "name": "Valid Task 2",
        "windowby_column": "salary",
        "window_checks_config": {"window": {"type": "tumbling", "params": {}}, "checks": []},
        "input": {"type": "kafka", "params": {}},
        "output": {"type": "jsonlines", "params": {}},
        "instant_checks": [
            {
                "name": "test_instant2",
                "check_class": "InRange",
                "params": {"column": "salary", "low": 10, "high": 500},
            }
        ],
    }

    response = client.post("/api/v1/bulk_create", json=[payload1, payload2])
    assert response.status_code == 201
    assert response.json()["task_ids"] == ["Valid Task 1", "Valid Task 2"]
    assert "Valid Task 1" in routes._TASKS_STORE
    assert "Valid Task 2" in routes._TASKS_STORE

    assert mock_build_task.call_count == 2
    assert mock_session.add_tasks.call_count == 2
    assert mock_task._start_pw_process.call_count == 2
