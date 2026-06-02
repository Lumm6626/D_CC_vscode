"""Self-Improving Agent core implementation."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from .database import MemoryDatabase
from .insights import InsightsGenerator

logger = logging.getLogger(__name__)


class SelfImprovingAgent:
    """An agent that learns from interactions and provides improvement suggestions."""

    def __init__(self, db_path: str):
        self.db = MemoryDatabase(db_path)
        self._last_insight_time = None
        self.scheduler = None
        self._config = {}
        self._daily_learning_job = None

    def record_conversation(
        self,
        agent_type: str,
        role: str,
        content: str,
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Record a conversation entry.

        Args:
            agent_type: Type of agent (e.g., 'lv-coordinator', 'ai-news')
            role: 'user' or 'assistant'
            content: The conversation content
            user_id: User identifier
            metadata: Optional additional metadata

        Returns:
            The ID of the inserted conversation record
        """
        return self.db.record_conversation(agent_type, role, content, user_id, metadata)

    def record_project(
        self,
        project_name: str,
        project_path: str,
        description: str = "",
        status: str = "in_progress",
        notes: str = ""
    ) -> int:
        """
        Record a project.

        Args:
            project_name: Name of the project
            project_path: Path to the project
            description: Project description
            status: 'completed', 'in_progress', or 'planned'
            notes: Additional notes

        Returns:
            The ID of the project record
        """
        return self.db.record_project(project_name, project_path, description, status, notes)

    def record_agent_execution(
        self,
        agent_type: str,
        task_type: str,
        task_description: str,
        status: str,
        output_summary: str = "",
        error_message: str = ""
    ) -> int:
        """
        Record an agent execution.

        Args:
            agent_type: Type of agent
            task_type: Type of task performed
            task_description: Description of the task
            status: 'success', 'failed', or 'skipped'
            output_summary: Summary of the output
            error_message: Error message if failed

        Returns:
            The ID of the log record
        """
        return self.db.record_agent_execution(
            agent_type, task_type, task_description, status, output_summary, error_message
        )

    def get_recent_conversations(self, limit: int = 50, agent_type: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict]:
        """Get recent conversations."""
        if user_id:
            return self.db.get_conversations_by_user(user_id, limit)
        return self.db.get_recent_conversations(limit, agent_type)

    def get_projects_summary(self, status: Optional[str] = None) -> List[Dict]:
        """Get projects summary."""
        return self.db.get_projects_summary(status)

    def get_suggestions(self) -> List[Dict]:
        """Get pending improvement suggestions."""
        return self.db.get_pending_suggestions()

    def generate_insight(self, confidence_threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        """
        Analyze conversations and logs to generate improvement insights.

        Args:
            confidence_threshold: Minimum confidence for an insight to be recorded

        Returns:
            The generated insight dict, or None if no significant insight found
        """
        insights = []

        # Analyze failed tasks
        failed_tasks = self.db.get_failed_tasks(limit=20)
        if len(failed_tasks) >= 3:
            # Group failures by agent_type
            failure_groups = {}
            for task in failed_tasks:
                agent = task["agent_type"]
                if agent not in failure_groups:
                    failure_groups[agent] = []
                failure_groups[agent].append(task)

            for agent_type, tasks in failure_groups.items():
                if len(tasks) >= 2:
                    task_types = [t["task_type"] for t in tasks]
                    error_messages = [t["error_message"] for t in tasks if t["error_message"]]

                    insight_content = f"Agent '{agent_type}' has {len(tasks)} recent failures. "
                    insight_content += f"Task types affected: {', '.join(set(task_types))}. "
                    if error_messages:
                        # Find common error patterns
                        insight_content += f"Common error pattern: {error_messages[0][:100]}..."

                    confidence = min(0.5 + (len(tasks) * 0.1), 0.95)
                    if confidence >= confidence_threshold:
                        insights.append({
                            "type": "improvement",
                            "title": f"High failure rate detected for {agent_type}",
                            "content": insight_content,
                            "confidence": confidence
                        })

        # Analyze project staleness
        projects = self.db.get_projects_summary(status="completed")
        stale_threshold_days = 30
        now = datetime.now()

        for project in projects:
            if project.get("updated_at"):
                try:
                    updated = datetime.fromisoformat(project["updated_at"])
                    days_since_update = (now - updated).days
                    if days_since_update > stale_threshold_days:
                        confidence = min(0.4 + (days_since_update * 0.01), 0.8)
                        if confidence >= confidence_threshold:
                            insights.append({
                                "type": "suggestion",
                                "title": f"Project '{project['project_name']}' may need attention",
                                "content": f"This project hasn't been updated in {days_since_update} days. "
                                          f"Consider reviewing or marking it as archived.",
                                "confidence": confidence
                            })
                except (ValueError, TypeError):
                    pass

        # Analyze task success rates
        stats = self.db.get_task_statistics(days=7)
        for agent_type, agent_stats in stats.items():
            total = agent_stats.get("success", 0) + agent_stats.get("failed", 0)
            if total >= 5:
                failure_rate = agent_stats.get("failed", 0) / total
                if failure_rate > 0.3:
                    confidence = min(0.5 + failure_rate * 0.3, 0.9)
                    if confidence >= confidence_threshold:
                        insights.append({
                            "type": "pattern",
                            "title": f"High failure rate for {agent_type}",
                            "content": f"Agent '{agent_type}' has a {failure_rate*100:.1f}% failure rate "
                                      f"over the past 7 days ({agent_stats.get('failed', 0)} failures "
                                      f"out of {total} tasks).",
                            "confidence": confidence
                        })

        # Store the highest confidence insight
        if insights:
            best_insight = max(insights, key=lambda x: x["confidence"])
            insight_id = self.db.record_insight(
                insight_type=best_insight["type"],
                title=best_insight["title"],
                content=best_insight["content"],
                confidence=best_insight["confidence"]
            )
            best_insight["id"] = insight_id
            return best_insight

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get overall agent statistics."""
        return self.db.get_database_stats()

    def get_task_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get task statistics for the last N days."""
        return self.db.get_task_statistics(days)

    def acknowledge_suggestion(self, suggestion_id: int) -> bool:
        """Acknowledge a suggestion."""
        return self.db.acknowledge_insight(suggestion_id)

    def get_all_insights(self, limit: int = 100) -> List[Dict]:
        """Get all insights."""
        return self.db.get_all_insights(limit)

    def cleanup_old_data(self, max_conversations: int = 10000) -> int:
        """Clean up old conversations to manage storage."""
        return self.db.cleanup_old_data(max_conversations)

    def set_config(self, config: Dict[str, Any]):
        """Set the agent configuration."""
        self._config = config

    def start_daily_scheduler(self):
        """Start the daily learning scheduler (default 12:00)."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            logger.warning("APScheduler not installed. Daily learning scheduler disabled.")
            return False

        if self.scheduler is not None:
            logger.info("Scheduler already running")
            return True

        daily_config = self._config.get("daily_learning", {})
        if not daily_config.get("enabled", True):
            logger.info("Daily learning is disabled in config")
            return False

        hour = daily_config.get("hour", 12)
        minute = daily_config.get("minute", 0)

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self.daily_learning_job,
            CronTrigger(hour=hour, minute=minute),
            id="daily_learning",
            name="Daily Learning Job",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"Daily learning scheduler started. Next run at {hour:02d}:{minute:02d}")
        return True

    def stop_daily_scheduler(self):
        """Stop the daily learning scheduler."""
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
            logger.info("Daily learning scheduler stopped")

    def daily_learning_job(self):
        """Daily learning main task - builds user profiles and generates insights."""
        logger.info("Starting daily learning job...")
        try:
            generator = InsightsGenerator(self.db)

            # Get all users with conversations in the last 24 hours
            user_ids = self.db.get_all_user_ids_last_24h()
            logger.info(f"Found {len(user_ids)} users with recent conversations")

            today = datetime.now().strftime("%Y-%m-%d")

            for user_id in user_ids:
                # Build user profile
                profile = generator.build_user_profile(user_id)
                logger.info(f"Built profile for user '{user_id}': {profile.get('interests', [])}")

                # Generate daily summary
                summary = generator.get_user_daily_summary(user_id, today)
                logger.info(f"Generated daily summary for user '{user_id}': {summary.get('conversation_count', 0)} conversations")

            # Generate all insights
            insights = generator.generate_all_insights()
            logger.info(f"Generated {len(insights)} insights")

            logger.info("Daily learning job completed successfully")
            return {
                "status": "success",
                "users_processed": len(user_ids),
                "insights_generated": len(insights)
            }

        except Exception as e:
            logger.error(f"Daily learning job failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def trigger_learning_now(self):
        """Manually trigger daily learning (for testing)."""
        logger.info("Manually triggered learning")
        return self.daily_learning_job()

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get the status of the daily learning scheduler."""
        if self.scheduler is None:
            return {"running": False, "enabled": False}

        job = self.scheduler.get_job("daily_learning")
        if job is None:
            return {"running": False, "enabled": True}

        next_run = None
        if job.next_run_time:
            next_run = job.next_run_time.isoformat()

        return {
            "running": self.scheduler.running,
            "enabled": True,
            "next_run": next_run
        }
