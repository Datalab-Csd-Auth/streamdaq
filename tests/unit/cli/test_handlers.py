from argparse import Namespace
from unittest.mock import patch

import pytest

from streamdaq.cli.handlers import serve, status
from streamdaq.measures.registry import MEASURE_REGISTRY


class TestServeHandler:
    @pytest.mark.parametrize("clear", [False, True])
    def test_creates_a_named_session_and_serves_it(self, clear):
        args = Namespace(
            host="0.0.0.0", port=9000, session="my_session", files=None, root="./", clear=clear
        )
        with (
            patch("streamdaq.cli.handlers.Session") as mock_session_cls,
            patch("streamdaq.cli.handlers.serve_session") as mock_serve,
        ):
            session = mock_session_cls.return_value
            serve(args)

        mock_session_cls.assert_called_once_with(
            name="my_session", clear=clear, root_path="./", files_path=None
        )
        mock_serve.assert_called_once_with(session, host="0.0.0.0", port=9000)

    def test_loads_custom_measure_file_when_files_is_set(self, tmp_path):
        measure_file = tmp_path / "handler_measure.py"
        measure_file.write_text(
            "from streamdaq.custom import measure\n\n\n"
            '@measure(["x"], name="_HandlerLoaded")\n'
            "def _handler_sum(d):\n"
            '    return sum(d["x"])\n'
        )
        args = Namespace(
            host="0.0.0.0",
            port=9000,
            session="my_session",
            files=str(measure_file),
            root=None,
            clear=False,
        )
        with (
            patch("streamdaq.cli.handlers.Session"),
            patch("streamdaq.cli.handlers.serve_session"),
        ):
            serve(args)

        assert "_HandlerLoaded" in MEASURE_REGISTRY


class TestStatusHandler:
    def test_exits_zero_when_api_is_running(self):
        args = Namespace(host="127.0.0.1", port=8080)
        with patch("streamdaq.cli.handlers.is_API_running", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                status(args)
        assert exc_info.value.code == 0

    def test_exits_one_when_api_is_not_running(self):
        args = Namespace(host="127.0.0.1", port=8080)
        with patch("streamdaq.cli.handlers.is_API_running", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                status(args)
        assert exc_info.value.code == 1
