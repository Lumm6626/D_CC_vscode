"""
SQLite Database operations for Schedule Secretary
"""
import sqlite3
import json
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any


def dict_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert sqlite3.Row to dict"""
    return dict(row)


class Database:
    def __init__(self, db_path: str = "schedule_secretary.db"):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    source TEXT DEFAULT 'manual',
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'pending',
                    due_date DATE,
                    estimated_hours REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Schedules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    date DATE NOT NULL,
                    start_time TIME,
                    end_time TIME,
                    slot_type TEXT DEFAULT 'task',
                    status TEXT DEFAULT 'scheduled',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
                )
            """)

            # Daily routines table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    time_of_day TIME NOT NULL,
                    days_of_week TEXT DEFAULT '[1,2,3,4,5]',
                    duration_minutes INTEGER DEFAULT 60,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Review history table for AI daily reviews
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS review_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_date DATE NOT NULL,
                    conversation_context TEXT DEFAULT '',
                    completed INTEGER DEFAULT 0,
                    summary TEXT DEFAULT '',
                    suggestions TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    # ==================== Task CRUD ====================

    def create_task(self, title: str, description: str = '', source: str = 'manual',
                    priority: str = 'normal', status: str = 'pending',
                    due_date: Optional[date] = None, estimated_hours: Optional[float] = None) -> int:
        """Create a new task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, source, priority, status, due_date, estimated_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, description, source, priority, status, due_date, estimated_hours))
            conn.commit()
            return cursor.lastrowid

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get a task by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict_from_row(row) if row else None

    def get_tasks(self, status: Optional[str] = None, source: Optional[str] = None,
                   priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks with optional filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)
            if source:
                query += " AND source = ?"
                params.append(source)
            if priority:
                query += " AND priority = ?"
                params.append(priority)

            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            return [dict_from_row(row) for row in cursor.fetchall()]

    def update_task(self, task_id: int, **kwargs) -> bool:
        """Update a task"""
        allowed_fields = ['title', 'description', 'source', 'priority', 'status', 'due_date', 'estimated_hours']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        updates['updated_at'] = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?",
                          list(updates.values()) + [task_id])
            conn.commit()
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        """Delete a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== Schedule CRUD ====================

    def create_schedule(self, date: date, start_time: Optional[time] = None,
                        end_time: Optional[time] = None, task_id: Optional[int] = None,
                        slot_type: str = 'task', status: str = 'scheduled') -> int:
        """Create a new schedule entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedules (task_id, date, start_time, end_time, slot_type, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, date, start_time, end_time, slot_type, status))
            conn.commit()
            return cursor.lastrowid

    def get_schedule(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
            row = cursor.fetchone()
            return dict_from_row(row) if row else None

    def get_schedules(self, date: Optional[date] = None,
                       status: Optional[str] = None,
                       slot_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get schedules with optional filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM schedules WHERE 1=1"
            params = []

            if date:
                query += " AND date = ?"
                params.append(date)
            if status:
                query += " AND status = ?"
                params.append(status)
            if slot_type:
                query += " AND slot_type = ?"
                params.append(slot_type)

            query += " ORDER BY date, start_time"
            cursor.execute(query, params)
            return [dict_from_row(row) for row in cursor.fetchall()]

    def get_schedules_with_tasks(self, date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get schedules joined with tasks"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT s.*, t.title as task_title, t.description as task_description,
                       t.priority as task_priority, t.status as task_status
                FROM schedules s
                LEFT JOIN tasks t ON s.task_id = t.id
                WHERE 1=1
            """
            params = []

            if date:
                query += " AND s.date = ?"
                params.append(date)

            query += " ORDER BY s.date, s.start_time"
            cursor.execute(query, params)
            return [dict_from_row(row) for row in cursor.fetchall()]

    def update_schedule(self, schedule_id: int, **kwargs) -> bool:
        """Update a schedule"""
        allowed_fields = ['task_id', 'date', 'start_time', 'end_time', 'slot_type', 'status']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        updates['updated_at'] = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            cursor.execute(f"UPDATE schedules SET {set_clause} WHERE id = ?",
                          list(updates.values()) + [schedule_id])
            conn.commit()
            return cursor.rowcount > 0

    def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== Daily Routine CRUD ====================

    def create_routine(self, title: str, time_of_day: time,
                       days_of_week: List[int] = None, duration_minutes: int = 60,
                       description: str = '', is_active: bool = True) -> int:
        """Create a new daily routine"""
        if days_of_week is None:
            days_of_week = [1, 2, 3, 4, 5]  # Weekdays by default

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO daily_routines (title, description, time_of_day, days_of_week, duration_minutes, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, description, time_of_day, json.dumps(days_of_week), duration_minutes, 1 if is_active else 0))
            conn.commit()
            return cursor.lastrowid

    def get_routine(self, routine_id: int) -> Optional[Dict[str, Any]]:
        """Get a routine by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_routines WHERE id = ?", (routine_id,))
            row = cursor.fetchone()
            if row:
                result = dict_from_row(row)
                result['days_of_week'] = json.loads(result['days_of_week'])
                result['is_active'] = bool(result['is_active'])
                return result
            return None

    def get_routines(self, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get all routines"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM daily_routines"
            params = []

            if is_active is not None:
                query += " WHERE is_active = ?"
                params.append(1 if is_active else 0)

            query += " ORDER BY time_of_day"
            cursor.execute(query, params)
            routines = []
            for row in cursor.fetchall():
                result = dict_from_row(row)
                result['days_of_week'] = json.loads(result['days_of_week'])
                result['is_active'] = bool(result['is_active'])
                routines.append(result)
            return routines

    def get_routines_for_day(self, day_of_week: int) -> List[Dict[str, Any]]:
        """Get active routines for a specific day of week (1=Monday, 7=Sunday)"""
        routines = self.get_routines(is_active=True)
        return [r for r in routines if day_of_week in r['days_of_week']]

    def update_routine(self, routine_id: int, **kwargs) -> bool:
        """Update a routine"""
        allowed_fields = ['title', 'description', 'time_of_day', 'days_of_week', 'duration_minutes', 'is_active']
        updates = {}

        for k, v in kwargs.items():
            if k in allowed_fields:
                if k == 'is_active':
                    updates[k] = 1 if v else 0
                elif k == 'days_of_week':
                    updates[k] = json.dumps(v) if isinstance(v, list) else v
                else:
                    updates[k] = v

        if not updates:
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            cursor.execute(f"UPDATE daily_routines SET {set_clause} WHERE id = ?",
                          list(updates.values()) + [routine_id])
            conn.commit()
            return cursor.rowcount > 0

    def delete_routine(self, routine_id: int) -> bool:
        """Delete a routine"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM daily_routines WHERE id = ?", (routine_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== Dashboard Stats ====================

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Task stats
            cursor.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
            task_stats = {row['status']: row['count'] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as total FROM tasks")
            total_tasks = cursor.fetchone()['total']

            # Today's schedule
            today = date.today().isoformat()
            cursor.execute("SELECT COUNT(*) as count FROM schedules WHERE date = ?", (today,))
            today_schedule_count = cursor.fetchone()['count']

            cursor.execute("""
                SELECT COUNT(*) as count FROM schedules
                WHERE date = ? AND status = 'done'
            """, (today,))
            today_completed_count = cursor.fetchone()['count']

            # Priority breakdown
            cursor.execute("SELECT priority, COUNT(*) as count FROM tasks WHERE status != 'completed' GROUP BY priority")
            priority_stats = {row['priority']: row['count'] for row in cursor.fetchall()}

            return {
                'total_tasks': total_tasks,
                'pending_tasks': task_stats.get('pending', 0),
                'in_progress_tasks': task_stats.get('in_progress', 0),
                'completed_tasks': task_stats.get('completed', 0),
                'today_schedule_count': today_schedule_count,
                'today_completed_count': today_completed_count,
                'pending_by_priority': priority_stats
            }

    # ==================== Review History CRUD ====================

    def create_review(self, review_date: date, conversation_context: str = '',
                     summary: str = '', suggestions: str = '') -> int:
        """Create a new review history entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO review_history (review_date, conversation_context, summary, suggestions)
                VALUES (?, ?, ?, ?)
            """, (review_date, conversation_context, summary, suggestions))
            conn.commit()
            return cursor.lastrowid

    def get_review(self, review_id: int) -> Optional[Dict[str, Any]]:
        """Get a review by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM review_history WHERE id = ?", (review_id,))
            row = cursor.fetchone()
            return dict_from_row(row) if row else None

    def get_reviews(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Get recent reviews"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM review_history
                ORDER BY review_date DESC
                LIMIT ?
            """, (limit,))
            return [dict_from_row(row) for row in cursor.fetchall()]

    def get_review_by_date(self, review_date: date) -> Optional[Dict[str, Any]]:
        """Get review for a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM review_history WHERE review_date = ?",
                (review_date.isoformat() if isinstance(review_date, date) else review_date,)
            )
            row = cursor.fetchone()
            return dict_from_row(row) if row else None

    def update_review(self, review_id: int, **kwargs) -> bool:
        """Update a review"""
        allowed_fields = ['conversation_context', 'completed', 'summary', 'suggestions']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        updates['updated_at'] = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            cursor.execute(f"UPDATE review_history SET {set_clause} WHERE id = ?",
                          list(updates.values()) + [review_id])
            conn.commit()
            return cursor.rowcount > 0

    def delete_review(self, review_id: int) -> bool:
        """Delete a review"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM review_history WHERE id = ?", (review_id,))
            conn.commit()
            return cursor.rowcount > 0


# Singleton instance
_db_instance: Optional[Database] = None


def get_db(db_path: str = None) -> Database:
    """Get database singleton instance"""
    global _db_instance
    if _db_instance is None:
        from config import Config
        _db_instance = Database(db_path or Config.DATABASE_PATH)
    return _db_instance
