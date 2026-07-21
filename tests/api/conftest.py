from streamdaq.api.app import set_active_session
from streamdaq.sessions.base import Session

test_session = Session(name="api_test_session")
set_active_session(test_session)


def make_mock_session():
    """Create a MagicMock session that shares the real test session's db.

    Tests that patch ``_get_session`` need the mock to carry a real
    LMDB ``db`` so that ``_get_tasks_store()`` can read/write
    task configs through the ``NamespaceStore``.
    """
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.db = test_session.db
    return mock
