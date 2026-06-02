"""
Entry point: start the video-subtitle web server.

Usage:
    python video-subtitle/run_web.py
    python video-subtitle/run_web.py --port 5003
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Video Subtitle Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5003, help="Bind port (default: 5003)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # Change to video-subtitle directory so relative imports work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from web.app import app

    print(f"Video Subtitle Web UI starting at http://localhost:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
