import tempfile

from streamdaq.api.app import StreamdaqApi
from streamdaq.sessions.base import Session

root_path = tempfile.mkdtemp(prefix="streamdaq-api-tests-")
test_session = Session(name="api_test_session", root_path=root_path)
test_api = StreamdaqApi(test_session)
app = test_api.app


def make_mock_session():
    """Create a MagicMock session that shares the real test session's db and store."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.db = test_session.db
    mock.get_tasks_store.side_effect = test_session.get_tasks_store
    return mock
