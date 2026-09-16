from unittest.mock import MagicMock, patch

from streamdaq.api.cli.run import main


def test_main_parses_args_and_dispatches_to_handler():
    handler = MagicMock()
    parsed = MagicMock(handler_function=handler)
    parser = MagicMock()
    parser.parse_args.return_value = parsed

    with patch("streamdaq.api.cli.run.build_parser", return_value=parser):
        main()

    parser.parse_args.assert_called_once_with()
    handler.assert_called_once_with(parsed)
