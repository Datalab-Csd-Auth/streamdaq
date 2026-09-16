import argparse
import sys

from streamdaq.api.app import set_active_session
from streamdaq.api.utils import is_API_running
from streamdaq.sessions.base import Session


def serve(args: argparse.Namespace):
    session = Session(name=args.session)
    set_active_session(session)
    print(f"✅ Initialized a streamdaq API session with name '{args.session}'.")
    print(f"🦆 Attempting to start streamdaq API on http://{args.host}:{args.port}.")
    print(f"ℹ️  Visit http://{args.host}:{args.port}/docs for API Swagger UI.\n")
    session.serve_api(host=args.host, port=args.port)


def status(args):
    if is_API_running(args.host, args.port):
        print(f"✅ 🦆 streamdaq API is RUNNING on http://{args.host}:{args.port}")
        sys.exit(0)

    print(f"❌ 🦆 streamdaq API is NOT running on http://{args.host}:{args.port}")
    sys.exit(1)
