from streamdaq.api.cli.parser import build_parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.handler_function(args)


if __name__ == "__main__":
    main()
