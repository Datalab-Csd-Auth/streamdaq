import argparse
import sys

from streamdaq.api.server import serve as serve_session
from streamdaq.api.utils import is_API_running
from streamdaq.orchestration.utils import load_additional_files
from streamdaq.sessions.base import Session


def serve(args: argparse.Namespace):
    session = Session(
        name=args.session,
        clear=args.clear,
        files_path=args.files,
        root_path=args.root,
    )
    print(f"🪡  Initialized a streamdaq API session with name '{args.session}'.")
    print(
        f"🌱 The streamdaq root directory is set to '{session.root_path}/' "
        f"{'(starting off clear)' if args.clear else '(reusing existing root)'}"
    )

    if args.files:
        load_additional_files(args.files)
        print(f"📄 Loaded additional Python files from '{args.files}'.")

    print(f"🦆 Attempting to start streamdaq API on http://{args.host}:{args.port}.")
    print(f"ℹ️  Visit http://{args.host}:{args.port}/docs for API Swagger UI.\n")
    serve_session(session, host=args.host, port=args.port)


def status(args):
    if is_API_running(args.host, args.port):
        print(f"✅ 🦆 streamdaq API is RUNNING on http://{args.host}:{args.port}")
        sys.exit(0)

    print(f"❌ 🦆 streamdaq API is NOT running on http://{args.host}:{args.port}")
    sys.exit(1)
