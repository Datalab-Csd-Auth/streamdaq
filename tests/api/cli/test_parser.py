import pytest

from streamdaq.api.cli.handlers import serve, status
from streamdaq.api.cli.parser import build_parser


class TestBuildParser:
    def test_serve_defaults(self):
        args = build_parser().parse_args(["serve"])
        assert args.command == "serve"
        assert args.host == "127.0.0.1"
        assert args.port == 8080
        assert args.session == "streamdaq_api_session"
        assert args.handler_function is serve

    def test_serve_custom_values(self):
        args = build_parser().parse_args(
            ["serve", "--host", "0.0.0.0", "--port", "9000", "--session", "my_session"]
        )
        assert (args.host, args.port, args.session) == ("0.0.0.0", 9000, "my_session")

    def test_serve_short_flags(self):
        args = build_parser().parse_args(["serve", "-H", "0.0.0.0", "-P", "9000", "-S", "s"])
        assert (args.host, args.port, args.session) == ("0.0.0.0", 9000, "s")

    def test_serve_files_long(self):
        args = build_parser().parse_args(["serve", "--files", "custom.py"])
        assert args.files == "custom.py"

    def test_serve_files_short(self):
        args = build_parser().parse_args(["serve", "-F", "custom.py"])
        assert args.files == "custom.py"

    def test_serve_files_default_none(self):
        args = build_parser().parse_args(["serve"])
        assert args.files is None

    def test_status_defaults_and_handler(self):
        args = build_parser().parse_args(["status"])
        assert args.command == "status"
        assert args.host == "127.0.0.1"
        assert args.port == 8080
        assert args.handler_function is status

    def test_status_has_no_session_argument(self):
        args = build_parser().parse_args(["status"])
        assert not hasattr(args, "session")

    def test_port_is_parsed_as_int(self):
        args = build_parser().parse_args(["serve", "--port", "1234"])
        assert args.port == 1234
        assert isinstance(args.port, int)

    def test_command_is_required(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args([])

    def test_unknown_command_is_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["non-existent"])
