from unittest.mock import MagicMock

import pytest

from streamdaq.api.app import (
    _DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS,
    get_active_session,
    set_active_session,
    shut_down_active_session,
)


@pytest.fixture(autouse=True)
def restore_active_session():
    original = get_active_session()
    yield
    set_active_session(original)


class TestShutDownActiveSession:
    def test_kills_active_session_with_default_timeout(self):
        session = MagicMock()
        set_active_session(session)
        shut_down_active_session()
        session.gracefully_kill.assert_called_once_with(_DEFAULT_GRACEFUL_KILL_TIMEOUT_SECONDS)

    def test_no_active_session_is_a_noop(self):
        set_active_session(None)
        shut_down_active_session()  # must not raise
