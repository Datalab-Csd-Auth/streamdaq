from streamdaq.sessions.base import Session

def main():
    print("Initializing StreamDAQ Session...")
    session = Session(name="live_api_session")
    
    print("Starting StreamDAQ API Control Plane on http://127.0.0.1:8000")
    print("Visit http://127.0.0.1:8000/docs for the interactive Swagger UI.")
    print("Waiting for tasks to be submitted via the API...\n")
    
    # Start the API server (this blocks the main thread)
    session.serve_api(port=8000)

if __name__ == "__main__":
    main()
