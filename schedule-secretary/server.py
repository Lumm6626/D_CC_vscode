#!/usr/bin/env python3
"""
Schedule Secretary - Main Entry Point
Intelligent Schedule Management System

Usage:
    python server.py                    # Start web server
    python server.py --init-db          # Initialize database
    python server.py --reminder-only     # Run reminder service only
"""

import os
import sys
import argparse

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def init_database():
    """Initialize the database"""
    from database import get_db
    print("Initializing database...")
    db = get_db()
    print("Database initialized successfully!")
    return db


def start_web_server(host="0.0.0.0", port=5001):
    """Start the Flask web server"""
    from web.app import app
    from reminder_service import get_reminder_service

    # Start Feishu WebSocket client
    from feishu.ws_client import start_ws_client
    feishu_client = start_ws_client()
    print("Feishu WebSocket client started")

    # Start reminder service in background
    reminder_service = get_reminder_service()
    reminder_service.start()
    print("Reminder service started")

    print(f"\n{'='*50}")
    print(f"Schedule Secretary Web Server")
    print(f"{'='*50}")
    print(f"Dashboard: http://localhost:{port}")
    print(f"Health: http://localhost:{port}/health")
    print(f"\nPress Ctrl+C to stop")
    print(f"{'='*50}\n")

    try:
        app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
        reminder_service.stop()


def run_reminder_service():
    """Run only the reminder service"""
    from reminder_service import get_reminder_service

    reminder_service = get_reminder_service()
    reminder_service.start()

    print("Reminder service is running. Press Ctrl+C to stop.")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        reminder_service.stop()


def main():
    parser = argparse.ArgumentParser(description="Schedule Secretary")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5001, help="Port to bind (default: 5001)")
    parser.add_argument("--init-db", action="store_true", help="Initialize database and exit")
    parser.add_argument("--reminder-only", action="store_true", help="Run reminder service only")

    args = parser.parse_args()

    if args.init_db:
        init_database()
        return

    if args.reminder_only:
        run_reminder_service()
        return

    start_web_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
