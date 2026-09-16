import json
from contextlib import contextmanager
from unittest.mock import patch
from urllib.error import URLError

from fastapi.testclient import TestClient

from streamdaq.api.app import app
from streamdaq.api.models import APIHeartbeat
from streamdaq.api.utils import is_API_running


@contextmanager
def _fake_response(status: int, body: dict | None):
    class _Response:
        def __init__(self):
            self.status = status

        def read(self):
            return json.dumps(body).encode()

    yield _Response()


class TestApiHeartbeatEndpoint:
    def test_heartbeat_returns_ok(self):
        response = TestClient(app).get("/api/v1/heartbeat")
        assert response.status_code == 200
        assert response.json() == {"status": "OK", "service": "streamdaq"}

    def test_api_heartbeat_model_defaults(self):
        assert APIHeartbeat().model_dump() == {"status": "OK", "service": "streamdaq"}


class TestIsApiRunning:
    def test_true_when_heartbeat_returns_ok(self):
        with patch(
            "streamdaq.api.utils.urlopen", return_value=_fake_response(200, {"status": "OK"})
        ):
            assert is_API_running("127.0.0.1", 8080) is True

    def test_false_on_non_200(self):
        with patch(
            "streamdaq.api.utils.urlopen", return_value=_fake_response(503, {"status": "OK"})
        ):
            assert is_API_running("127.0.0.1", 8080) is False

    def test_false_when_connection_fails(self):
        with patch("streamdaq.api.utils.urlopen", side_effect=URLError("refused")):
            assert is_API_running("127.0.0.1", 8080) is False
