import argparse
from dataclasses import dataclass
from typing import Any

from streamdaq.api.cli.handlers import serve, status


@dataclass
class Argument:
    short_name: str
    long_name: str
    dtype: type
    default_value: Any | None
    help_text: str | None

    @property
    def args(self) -> tuple:
        return ("-" + self.short_name, "--" + self.long_name)

    @property
    def kwargs(self) -> dict:
        return {
            "type": self.dtype,
            "default": self.default_value,
            "help": self.help_text + f" (default: {self.default_value})",
        }


PORT = Argument("P", "port", int, 8080, "Port for the API server")
HOST = Argument("H", "host", str, "127.0.0.1", "Host address for the API server")
SESSION = Argument("S", "session", str, "streamdaq_api_session", "The streamdaq API session name")


def _build_serve_parser(serve_parser: argparse.ArgumentParser) -> None:
    serve_parser.add_argument(*PORT.args, **PORT.kwargs)
    serve_parser.add_argument(*HOST.args, **HOST.kwargs)
    serve_parser.add_argument(*SESSION.args, **SESSION.kwargs)
    serve_parser.set_defaults(handler_function=serve)


def _build_status_parser(status_parser: argparse.ArgumentParser) -> None:
    status_parser.add_argument(*PORT.args, **PORT.kwargs)
    status_parser.add_argument(*HOST.args, **HOST.kwargs)
    status_parser.set_defaults(handler_function=status)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="streamdaq")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # `streamdaq serve`
    serve_parser = subparsers.add_parser(name="serve", help="Start the streamdaq API.")
    _build_serve_parser(serve_parser)

    # `streamdaq status`
    status_parser = subparsers.add_parser(name="status", help="Check API is up and running.")
    _build_status_parser(status_parser)

    return parser
