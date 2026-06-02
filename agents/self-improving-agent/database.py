"""Database operations for Self-Improving Agent."""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class MemoryDatabase:
    """SQLite database wrapper for agent memory storage."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_type TEXT,
                    user_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)

            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT,
                    project_path TEXT,
                    description TEXT,
                    status TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    notes TEXT
                )
            """)

            # Agent logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_type TEXT,
                    task_type TEXT,
                    task_description TEXT,
                    status TEXT,
                    output_summary TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT
                )
            """)

            # Insights table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    insight_type TEXT,
                    title TEXT,
                    content TEXT,
                    confidence REAL,
                    source_conversation_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_acknowledged BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (source_conversation_id) REFERENCES conversations(id)
                )
            """)

            # User profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    interests TEXT,
                    topic_expertise TEXT,
                    communication_style TEXT DEFAULT "mixed",
                    preferred_response_length TEXT DEFAULT "medium",
                    active_hours TEXT,
                    total_conversations INTEGER DEFAULT 0,
                    last_updated DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Daily summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    summary_date DATE NOT NULL,
                    conversation_count INTEGER DEFAULT 0,
                    topics_discussed TEXT,
                    avg_conversation_length REAL DEFAULT 0.0,
                    agent_types_interacted TEXT,
                    dominant_sentiment TEXT,
                    summary_text TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, summary_date)
                )
            """)

            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_agent_type ON conversations(agent_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON agent_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_status ON agent_logs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_acknowledged ON insights(is_acknowledged)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_summaries_user_date ON daily_summaries(user_id, summary_date)")

            conn.commit()

    # Conversation operations
    def record_conversation(
        self,
        agent_type: str,
        role: str,
        content: str,
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Record a conversation entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversations (agent_type, user_id, role, content, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (agent_type, user_id, role, content, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_conversations(self, limit: int = 50, agent_type: Optional[str] = None) -> List[Dict]:
        """Get recent conversations, optionally filtered by agent type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if agent_type:
                cursor.execute(
                    """
                    SELECT * FROM conversations
                    WHERE agent_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (agent_type, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_conversations_by_user(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get conversations for a specific user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # Project operations
    def record_project(
        self,
        project_name: str,
        project_path: str,
        description: str = "",
        status: str = "in_progress",
        notes: str = ""
    ) -> int:
        """Record a new project or update existing one."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # Check if project exists
            cursor.execute("SELECT id FROM projects WHERE project_name = ?", (project_name,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE projects
                    SET project_path = ?, description = ?, status = ?, updated_at = ?, notes = ?
                    WHERE project_name = ?
                    """,
                    (project_path, description, status, now, notes, project_name)
                )
                conn.commit()
                return existing["id"]
            else:
                cursor.execute(
                    """
                    INSERT INTO projects (project_name, project_path, description, status, created_at, updated_at, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (project_name, project_path, description, status, now, now, notes)
                )
                conn.commit()
                return cursor.lastrowid

    def update_project_status(self, project_name: str, status: str) -> bool:
        """Update project status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE projects
                SET status = ?, updated_at = ?
                WHERE project_name = ?
                """,
                (status, datetime.now().isoformat(), project_name)
            )
            conn.commit()
            return cursor.rowcount > 0

    def add_project_note(self, project_name: str, note: str) -> bool:
        """Add a note to a project."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT notes FROM projects WHERE project_name = ?
                """,
                (project_name,)
            )
            row = cursor.fetchone()
            if row:
                existing_notes = row["notes"] or ""
                new_notes = existing_notes + f"\n[{datetime.now().isoformat()}] {note}"
                cursor.execute(
                    """
                    UPDATE projects SET notes = ?, updated_at = ? WHERE project_name = ?
                    """,
                    (new_notes, datetime.now().isoformat(), project_name)
                )
                conn.commit()
                return True
            return False

    def get_projects_summary(self, status: Optional[str] = None) -> List[Dict]:
        """Get projects summary, optionally filtered by status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC",
                    (status,)
                )
            else:
                cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_project(self, project_name: str) -> Optional[Dict]:
        """Get a specific project by name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE project_name = ?", (project_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # Agent log operations
    def record_agent_execution(
        self,
        agent_type: str,
        task_type: str,
        task_description: str,
        status: str,
        output_summary: str = "",
        error_message: str = ""
    ) -> int:
        """Record an agent execution log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO agent_logs (agent_type, task_type, task_description, status, output_summary, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (agent_type, task_type, task_description, status, output_summary, error_message)
            )
            conn.commit()
            return cursor.lastrowid

    def get_agent_logs(
        self,
        agent_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get agent logs with optional filters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM agent_logs WHERE 1=1"
            params = []

            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_failed_tasks(self, limit: int = 50) -> List[Dict]:
        """Get recent failed tasks."""
        return self.get_agent_logs(status="failed", limit=limit)

    def get_task_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get task statistics for the last N days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    agent_type,
                    status,
                    COUNT(*) as count
                FROM agent_logs
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                GROUP BY agent_type, status
                """,
                (days,)
            )
            rows = cursor.fetchall()
            stats = {}
            for row in rows:
                if row["agent_type"] not in stats:
                    stats[row["agent_type"]] = {"success": 0, "failed": 0, "skipped": 0}
                stats[row["agent_type"]][row["status"]] = row["count"]
            return stats

    # Insights operations
    def record_insight(
        self,
        insight_type: str,
        title: str,
        content: str,
        confidence: float,
        source_conversation_id: Optional[int] = None
    ) -> int:
        """Record a new insight."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO insights (insight_type, title, content, confidence, source_conversation_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (insight_type, title, content, confidence, source_conversation_id)
            )
            conn.commit()
            return cursor.lastrowid

    def get_pending_suggestions(self) -> List[Dict]:
        """Get unacknowledged suggestions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM insights
                WHERE is_acknowledged = FALSE AND insight_type = 'suggestion'
                ORDER BY confidence DESC, created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_insights(self, limit: int = 100) -> List[Dict]:
        """Get all insights."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM insights
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def acknowledge_insight(self, insight_id: int) -> bool:
        """Mark an insight as acknowledged."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE insights SET is_acknowledged = TRUE WHERE id = ?",
                (insight_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_recent_insights(self, days: int = 7) -> List[Dict]:
        """Get insights from the last N days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM insights
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
                """,
                (days,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # User profile operations
    def upsert_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> int:
        """Insert or update a user profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                SELECT id FROM user_profiles WHERE user_id = ?
                """,
                (user_id,)
            )
            existing = cursor.fetchone()

            interests = profile_data.get("interests")
            topic_expertise = profile_data.get("topic_expertise")
            active_hours = profile_data.get("active_hours")

            if existing:
                cursor.execute(
                    """
                    UPDATE user_profiles
                    SET display_name = ?, interests = ?, topic_expertise = ?,
                        communication_style = ?, preferred_response_length = ?,
                        active_hours = ?, total_conversations = ?, last_updated = ?
                    WHERE user_id = ?
                    """,
                    (
                        profile_data.get("display_name"),
                        json.dumps(interests) if interests else None,
                        json.dumps(topic_expertise) if topic_expertise else None,
                        profile_data.get("communication_style", "mixed"),
                        profile_data.get("preferred_response_length", "medium"),
                        json.dumps(active_hours) if active_hours else None,
                        profile_data.get("total_conversations", 0),
                        now,
                        user_id
                    )
                )
                conn.commit()
                return existing["id"]
            else:
                cursor.execute(
                    """
                    INSERT INTO user_profiles
                    (user_id, display_name, interests, topic_expertise, communication_style,
                     preferred_response_length, active_hours, total_conversations, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        profile_data.get("display_name"),
                        json.dumps(interests) if interests else None,
                        json.dumps(topic_expertise) if topic_expertise else None,
                        profile_data.get("communication_style", "mixed"),
                        profile_data.get("preferred_response_length", "medium"),
                        json.dumps(active_hours) if active_hours else None,
                        profile_data.get("total_conversations", 0),
                        now
                    )
                )
                conn.commit()
                return cursor.lastrowid

    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get a user profile by user_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Parse JSON fields
                for field in ["interests", "topic_expertise", "active_hours"]:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                return result
            return None

    def get_all_user_profiles(self) -> List[Dict]:
        """Get all user profiles."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profiles ORDER BY last_updated DESC")
            rows = cursor.fetchall()
            profiles = []
            for row in rows:
                result = dict(row)
                for field in ["interests", "topic_expertise", "active_hours"]:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                profiles.append(result)
            return profiles

    # Daily summary operations
    def upsert_daily_summary(self, user_id: str, summary_date: str, summary_data: Dict[str, Any]) -> int:
        """Insert or update a daily summary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id FROM daily_summaries WHERE user_id = ? AND summary_date = ?
                """,
                (user_id, summary_date)
            )
            existing = cursor.fetchone()

            topics = summary_data.get("topics_discussed")
            agent_types = summary_data.get("agent_types_interacted")

            if existing:
                cursor.execute(
                    """
                    UPDATE daily_summaries
                    SET conversation_count = ?, topics_discussed = ?, avg_conversation_length = ?,
                        agent_types_interacted = ?, dominant_sentiment = ?, summary_text = ?
                    WHERE user_id = ? AND summary_date = ?
                    """,
                    (
                        summary_data.get("conversation_count", 0),
                        json.dumps(topics) if topics else None,
                        summary_data.get("avg_conversation_length", 0.0),
                        json.dumps(agent_types) if agent_types else None,
                        summary_data.get("dominant_sentiment"),
                        summary_data.get("summary_text"),
                        user_id,
                        summary_date
                    )
                )
                conn.commit()
                return existing["id"]
            else:
                cursor.execute(
                    """
                    INSERT INTO daily_summaries
                    (user_id, summary_date, conversation_count, topics_discussed,
                     avg_conversation_length, agent_types_interacted, dominant_sentiment, summary_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        summary_date,
                        summary_data.get("conversation_count", 0),
                        json.dumps(topics) if topics else None,
                        summary_data.get("avg_conversation_length", 0.0),
                        json.dumps(agent_types) if agent_types else None,
                        summary_data.get("dominant_sentiment"),
                        summary_data.get("summary_text")
                    )
                )
                conn.commit()
                return cursor.lastrowid

    def get_daily_summary(self, user_id: str, summary_date: str) -> Optional[Dict]:
        """Get a daily summary for a specific user and date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM daily_summaries WHERE user_id = ? AND summary_date = ?",
                (user_id, summary_date)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                for field in ["topics_discussed", "agent_types_interacted"]:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                return result
            return None

    def get_daily_summaries_range(self, user_id: str, start_date: str, end_date: str) -> List[Dict]:
        """Get daily summaries for a date range."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM daily_summaries
                WHERE user_id = ? AND summary_date >= ? AND summary_date <= ?
                ORDER BY summary_date DESC
                """,
                (user_id, start_date, end_date)
            )
            rows = cursor.fetchall()
            summaries = []
            for row in rows:
                result = dict(row)
                for field in ["topics_discussed", "agent_types_interacted"]:
                    if result.get(field):
                        try:
                            result[field] = json.loads(result[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                summaries.append(result)
            return summaries

    def get_conversations_in_range(self, user_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get conversations for a user within a time range."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM conversations
                WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
                """,
                (user_id, start_time.isoformat(), end_time.isoformat())
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_user_ids_last_24h(self) -> List[str]:
        """Get all unique user_ids with conversations in the last 24 hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT user_id FROM conversations
                WHERE timestamp >= datetime('now', '-1 day')
                """
            )
            rows = cursor.fetchall()
            return [row["user_id"] for row in rows if row["user_id"]]

    # Utility operations
    def cleanup_old_data(self, max_conversations: int = 10000) -> int:
        """Remove old conversations to keep storage under control."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            count = cursor.fetchone()["count"]

            if count > max_conversations:
                delete_count = count - max_conversations
                cursor.execute(
                    """
                    DELETE FROM conversations WHERE id IN (
                        SELECT id FROM conversations ORDER BY timestamp ASC LIMIT ?
                    )
                    """,
                    (delete_count,)
                )
                conn.commit()
                return delete_count
            return 0

    def get_database_stats(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            stats = {}

            # Count tables
            for table in ["conversations", "projects", "agent_logs", "insights"]:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()["count"]

            # Recent activity
            cursor.execute(
                "SELECT COUNT(*) as count FROM conversations WHERE timestamp >= datetime('now', '-1 day')"
            )
            stats["conversations_last_24h"] = cursor.fetchone()["count"]

            cursor.execute(
                "SELECT COUNT(*) as count FROM agent_logs WHERE timestamp >= datetime('now', '-1 day')"
            )
            stats["logs_last_24h"] = cursor.fetchone()["count"]

            return stats
