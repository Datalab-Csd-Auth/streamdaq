from streamdaq.api.app import set_active_session
from streamdaq.sessions.base import Session

# Expose a pre-configured app instance for Uvicorn hot-reloading
_dev_session = Session(name="streamdaq_api_session_dev")
set_active_session(_dev_session)


def main():
    print("Initializing StreamDAQ Session...")
    session = Session(name="streamdaq_api_session")

    print("Starting StreamDAQ API Control Plane on http://127.0.0.1:8080")
    print("Visit http://127.0.0.1:8080/docs for the interactive Swagger UI.")
    print("Waiting for tasks to be submitted via the API...\n")

    # Start the API server (this blocks the main thread)
    session.serve_api(port=8080)


if __name__ == "__main__":
    main()
