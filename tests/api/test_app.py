from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from streamdaq.api.app import StreamdaqApi
from streamdaq.api.utils import DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS


class TestApiLifespan:
    def _initialize_session_and_api(self) -> tuple:
        session = MagicMock()
        api = StreamdaqApi(session)
        return session, api

    def test_shutdown_gracefully_kills_the_owned_session(self):
        session, api = self._initialize_session_and_api()
        with TestClient(api.app):
            session.gracefully_kill.assert_not_called()
        session.gracefully_kill.assert_called_once_with(DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS)

    def test_session_is_exposed_on_app_state(self):
        session, api = self._initialize_session_and_api()
        assert api.app.state.session is session
