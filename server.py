import http.server
import socketserver
import os

PORT = 12345
DIRECTORY = "docs"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    # Ensure we are in the right directory or change to it
    # Assuming the script is run from the project root e:\pyProject\jw3_bz
    # and docs is a subdirectory.
    
    if not os.path.exists(DIRECTORY):
        print(f"Error: Directory '{DIRECTORY}' not found.")
        exit(1)

    print(f"Serving '{DIRECTORY}' at http://localhost:{PORT}")
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print("Press Ctrl+C to stop.")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error: {e}")
