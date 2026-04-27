#!/usr/bin/env python3
"""Server entry point for Self-Improving Agent."""

import os
import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from self_improving_agent.agent import SelfImprovingAgent
from self_improving_agent.web import WebServer


def load_config(config_path: str = None) -> dict:
    """Load configuration from file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.json"
    else:
        config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Default config
    return {
        "database_path": "self-improving-agent/memory.db",
        "auto_insight_interval_hours": 24,
        "max_conversations_stored": 10000,
        "suggestion_frequency": "daily",
        "insight_confidence_threshold": 0.7
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Self-Improving Agent Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--db-path", help="Path to database file")
    parser.add_argument("--no-scheduler", action="store_true", help="Disable daily learning scheduler")

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Determine database path
    if args.db_path:
        db_path = args.db_path
    else:
        # Make path relative to the script location
        script_dir = Path(__file__).parent
        db_path = script_dir / config.get("database_path", "memory.db")

    # Ensure absolute path
    if not Path(db_path).is_absolute():
        db_path = Path(__file__).parent / db_path

    print(f"Initializing Self-Improving Agent...")
    print(f"Database: {db_path}")

    # Initialize agent
    agent = SelfImprovingAgent(str(db_path))
    agent.set_config(config)

    # Show initial stats
    stats = agent.get_stats()
    print(f"Database stats: {stats['conversations_count']} conversations, "
          f"{stats['projects_count']} projects, "
          f"{stats['agent_logs_count']} logs, "
          f"{stats['insights_count']} insights")

    # Start daily scheduler if not disabled
    if not args.no_scheduler:
        agent.start_daily_scheduler()

    # Start web server
    server = WebServer(agent, host=args.host, port=args.port)
    server.start(blocking=True)


if __name__ == "__main__":
    main()
