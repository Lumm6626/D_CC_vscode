"""Web interface for Self-Improving Agent."""

import json
from typing import Dict, Any, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

from .agent import SelfImprovingAgent


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the web API."""

    agent: Optional[SelfImprovingAgent] = None

    def _send_json(self, data: Any, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _send_text(self, text: str, status: int = 200):
        """Send plain text response."""
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path == "/api/health":
                self._send_json({"status": "ok", "agent": "self-improving-agent"})

            elif path == "/api/stats":
                stats = self.agent.get_stats()
                self._send_json(stats)

            elif path == "/api/conversations":
                limit = int(query.get("limit", ["50"])[0])
                agent_type = query.get("agent_type", [None])[0]
                conversations = self.agent.get_recent_conversations(limit=limit, agent_type=agent_type)
                self._send_json({"conversations": conversations, "count": len(conversations)})

            elif path == "/api/conversations/user":
                user_id = query.get("user_id", ["default"])[0]
                limit = int(query.get("limit", ["50"])[0])
                conversations = self.agent.get_recent_conversations(limit=limit, user_id=user_id)
                self._send_json({"conversations": conversations, "count": len(conversations)})

            elif path == "/api/projects":
                status = query.get("status", [None])[0]
                projects = self.agent.get_projects_summary(status=status)
                self._send_json({"projects": projects, "count": len(projects)})

            elif path == "/api/suggestions":
                suggestions = self.agent.get_suggestions()
                self._send_json({"suggestions": suggestions, "count": len(suggestions)})

            elif path == "/api/insights":
                limit = int(query.get("limit", ["100"])[0])
                insights = self.agent.get_all_insights(limit=limit)
                self._send_json({"insights": insights, "count": len(insights)})

            elif path == "/api/logs":
                agent_type = query.get("agent_type", [None])[0]
                status = query.get("status", [None])[0]
                limit = int(query.get("limit", ["100"])[0])
                logs = self.agent.db.get_agent_logs(agent_type=agent_type, status=status, limit=limit)
                self._send_json({"logs": logs, "count": len(logs)})

            elif path == "/api/task-stats":
                days = int(query.get("days", ["7"])[0])
                stats = self.agent.get_task_statistics(days=days)
                self._send_json(stats)

            elif path == "/api/user-profiles":
                profiles = self.agent.db.get_all_user_profiles()
                self._send_json({"profiles": profiles, "count": len(profiles)})

            elif path == "/api/user-profile":
                user_id = query.get("user_id", [None])[0]
                if user_id:
                    profile = self.agent.db.get_user_profile(user_id)
                    if profile:
                        self._send_json(profile)
                    else:
                        self._send_json({"error": "Profile not found"}, 404)
                else:
                    self._send_json({"error": "user_id parameter required"}, 400)

            elif path == "/api/daily-summaries":
                user_id = query.get("user_id", [None])[0]
                days = int(query.get("days", ["7"])[0])
                if user_id:
                    from datetime import datetime, timedelta
                    end_date = datetime.now().strftime("%Y-%m-%d")
                    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                    summaries = self.agent.db.get_daily_summaries_range(user_id, start_date, end_date)
                    self._send_json({"summaries": summaries, "count": len(summaries)})
                else:
                    self._send_json({"error": "user_id parameter required"}, 400)

            elif path == "/api/learning/status":
                status = self.agent.get_scheduler_status()
                self._send_json(status)

            elif path == "/":
                self._send_text(
                    "Self-Improving Agent API\n"
                    "=======================\n\n"
                    "Endpoints:\n"
                    "  GET /api/health              - Health check\n"
                    "  GET /api/stats               - Database statistics\n"
                    "  GET /api/conversations       - Recent conversations\n"
                    "  GET /api/projects            - Project list\n"
                    "  GET /api/suggestions         - Pending suggestions\n"
                    "  GET /api/insights            - All insights\n"
                    "  GET /api/logs                - Agent execution logs\n"
                    "  GET /api/task-stats          - Task statistics\n"
                    "  GET /api/user-profiles       - All user profiles\n"
                    "  GET /api/user-profile        - Get specific user profile\n"
                    "  GET /api/daily-summaries     - Get daily summaries\n"
                    "  GET /api/learning/status     - Scheduler status\n\n"
                    "  POST /api/conversations      - Record a conversation\n"
                    "  POST /api/projects           - Record a project\n"
                    "  POST /api/logs               - Record agent execution\n"
                    "  POST /api/insights/generate  - Trigger insight generation\n"
                    "  POST /api/suggestions/ack    - Acknowledge a suggestion\n"
                    "  POST /api/learning/trigger   - Trigger daily learning\n"
                )

            else:
                self._send_json({"error": "Not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            data = json.loads(body) if body else {}

            if path == "/api/conversations":
                # Record a conversation
                conversation_id = self.agent.record_conversation(
                    agent_type=data.get("agent_type", "unknown"),
                    role=data.get("role", "assistant"),
                    content=data.get("content", ""),
                    user_id=data.get("user_id", "default"),
                    metadata=data.get("metadata")
                )
                self._send_json({"id": conversation_id, "status": "recorded"})

            elif path == "/api/projects":
                # Record a project
                project_id = self.agent.record_project(
                    project_name=data.get("project_name", "unnamed"),
                    project_path=data.get("project_path", ""),
                    description=data.get("description", ""),
                    status=data.get("status", "in_progress"),
                    notes=data.get("notes", "")
                )
                self._send_json({"id": project_id, "status": "recorded"})

            elif path == "/api/projects/update-status":
                # Update project status
                success = self.agent.db.update_project_status(
                    project_name=data.get("project_name"),
                    status=data.get("status")
                )
                self._send_json({"success": success})

            elif path == "/api/projects/add-note":
                # Add note to project
                success = self.agent.db.add_project_note(
                    project_name=data.get("project_name"),
                    note=data.get("note", "")
                )
                self._send_json({"success": success})

            elif path == "/api/logs":
                # Record agent execution
                log_id = self.agent.record_agent_execution(
                    agent_type=data.get("agent_type", "unknown"),
                    task_type=data.get("task_type", "general"),
                    task_description=data.get("task_description", ""),
                    status=data.get("status", "success"),
                    output_summary=data.get("output_summary", ""),
                    error_message=data.get("error_message", "")
                )
                self._send_json({"id": log_id, "status": "recorded"})

            elif path == "/api/insights/generate":
                # Trigger insight generation
                from .insights import InsightsGenerator
                generator = InsightsGenerator(self.agent.db)
                confidence_threshold = float(query.get("confidence", ["0.7"])[0])
                insights = generator.generate_all_insights(confidence_threshold=confidence_threshold)
                self._send_json({"insights_generated": len(insights), "insights": insights})

            elif path == "/api/suggestions/ack":
                # Acknowledge a suggestion
                suggestion_id = data.get("id")
                success = self.agent.acknowledge_suggestion(suggestion_id)
                self._send_json({"success": success})

            elif path == "/api/cleanup":
                # Clean up old data
                max_conversations = int(data.get("max_conversations", 10000))
                deleted = self.agent.cleanup_old_data(max_conversations)
                self._send_json({"deleted": deleted})

            elif path == "/api/learning/trigger":
                # Manually trigger daily learning
                result = self.agent.trigger_learning_now()
                self._send_json(result)

            else:
                self._send_json({"error": "Not found"}, 404)

        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def log_message(self, format, *args):
        """Suppress default logging to reduce noise."""
        pass


class WebServer:
    """Web server wrapper for the Self-Improving Agent."""

    def __init__(self, agent: SelfImprovingAgent, host: str = "0.0.0.0", port: int = 8080):
        self.agent = agent
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self, blocking: bool = True):
        """Start the web server."""
        RequestHandler.agent = self.agent

        self.server = HTTPServer((self.host, self.port), RequestHandler)
        print(f"Starting Self-Improving Agent server on {self.host}:{self.port}")
        print(f"API documentation available at http://localhost:{self.port}/")

        if blocking:
            try:
                self.server.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down server...")
                self.server.shutdown()
        else:
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return self

    def stop(self):
        """Stop the web server."""
        if self.server:
            self.server.shutdown()
            if self.thread:
                self.thread.join(timeout=5)
