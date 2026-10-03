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

    from streamdaq.api.models import TaskConfig
    from streamdaq.storage.lmdb_store import NamespaceStore

    mock = MagicMock()
    mock.db = test_session.db
    mock.tasks_store.side_effect = lambda: NamespaceStore(
        test_session.db, "api_tasks", value_type=TaskConfig
    )
    return mock
