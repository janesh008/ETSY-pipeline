import os
import sys
import subprocess
import webbrowser
import time

def ensure_dependencies():
    """Checks and installs Flask if not present."""
    try:
        import flask
    except ImportError:
        print("Flask not found. Installing Flask...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
            print("Flask successfully installed!")
        except Exception as e:
            print(f"Failed to install Flask via pip: {e}")
            print("Please run: pip install flask")
            sys.exit(1)

def main():
    ensure_dependencies()
    
    server_script = os.path.join("web_editor", "server.py")
    if not os.path.exists(server_script):
        print(f"Error: Server script not found at {server_script}")
        sys.exit(1)

    print("Starting Web Editor backend on http://127.0.0.1:5000 ...")
    
    # Run the Flask server
    # We run it as a subprocess so we can launch the web browser and keep running
    try:
        # Launch browser after a short delay to let the server bind
        def launch_browser():
            time.sleep(1.5)
            print("Opening web editor in your browser...")
            webbrowser.open("http://127.0.0.1:5000")
            
        import threading
        threading.Thread(target=launch_browser, daemon=True).start()
        
        # Start server blockingly in main thread
        subprocess.run([sys.executable, server_script])
    except KeyboardInterrupt:
        print("\nShutting down Web Editor.")
    except Exception as e:
        print(f"Error running Web Editor: {e}")

if __name__ == "__main__":
    main()
