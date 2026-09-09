"""Tests for the UI liveness probe ``_is_ui_up``.

The probe opens a URL with a short timeout; we patch ``urlopen`` so no real
network call is made and both the reachable and unreachable branches are
exercised, including the ``STREAMDAQ_UI_URL`` override.
"""

from unittest.mock import MagicMock, patch

from streamdaq.utils import ui


class TestIsUiUp:
    def test_returns_true_when_default_url_reachable(self, monkeypatch):
        monkeypatch.delenv("STREAMDAQ_UI_URL", raising=False)
        with patch.object(ui.urllib.request, "urlopen", return_value=MagicMock()):
            assert ui._is_ui_up() is True

    def test_returns_false_when_unreachable(self, monkeypatch):
        monkeypatch.delenv("STREAMDAQ_UI_URL", raising=False)
        with patch.object(ui.urllib.request, "urlopen", side_effect=OSError("refused")):
            assert ui._is_ui_up() is False

    def test_uses_env_var_url_when_set(self, monkeypatch):
        monkeypatch.setenv("STREAMDAQ_UI_URL", "http://custom-ui:9999")
        with patch.object(ui.urllib.request, "urlopen", return_value=MagicMock()) as mock_open:
            assert ui._is_ui_up() is True
            assert mock_open.call_args.args[0] == "http://custom-ui:9999"
