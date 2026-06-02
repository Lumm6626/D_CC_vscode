"""Insights generation logic for Self-Improving Agent."""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict


class InsightsGenerator:
    """Generate insights from agent data."""

    # Topic keywords for extraction
    TOPIC_KEYWORDS = {
        "AI": ["ai", "artificial intelligence", "machine learning", "deep learning", "neural", "gpt", "llm", "模型", "人工智能", "机器学习"],
        "医疗": ["medical", "health", "doctor", "hospital", "医疗", "健康", "医院", "疾病", "medicine"],
        "项目管理": ["project", "task", "deadline", "sprint", "agile", "scrum", "项目", "任务", "敏捷", "冲刺"],
        "编程": ["code", "programming", "debug", "api", "function", "class", "bug", "代码", "编程", "函数", "调试"],
        "新闻": ["news", "event", "update", "announcement", "新闻", "事件", "动态", "公告"],
        "财务": ["money", "finance", "cost", "budget", "revenue", "财务", "成本", "预算", "收入"],
        "旅行": ["travel", "trip", "flight", "hotel", "destination", "旅行", "航班", "酒店", "旅游"],
        "教育": ["learn", "course", "study", "education", "培训", "学习", "课程", "教育"],
    }

    # Sentiment keywords
    POSITIVE_WORDS = ["good", "great", "excellent", "amazing", "wonderful", "perfect", "love", "like", "happy", "太好了", "很好", "喜欢", "优秀", "棒"]
    NEGATIVE_WORDS = ["bad", "terrible", "awful", "hate", "dislike", "sad", "angry", "fail", "error", "问题", "错误", "失败", "糟糕", "讨厌"]

    def __init__(self, db):
        self.db = db

    def analyze_failure_patterns(self, days: int = 7, min_failures: int = 2) -> List[Dict[str, Any]]:
        """Analyze failure patterns in agent logs."""
        insights = []

        logs = self.db.get_agent_logs(status="failed", limit=100)
        cutoff = datetime.now() - timedelta(days=days)

        recent_failures = []
        for log in logs:
            try:
                log_time = datetime.fromisoformat(log["timestamp"])
                if log_time >= cutoff:
                    recent_failures.append(log)
            except (ValueError, TypeError):
                pass

        if len(recent_failures) < min_failures:
            return insights

        # Group by agent_type and task_type
        by_agent = defaultdict(list)
        by_agent_task = defaultdict(list)

        for failure in recent_failures:
            by_agent[failure["agent_type"]].append(failure)
            key = f"{failure['agent_type']}:{failure['task_type']}"
            by_agent_task[key].append(failure)

        # Generate insights for agents with multiple failures
        for agent_type, failures in by_agent.items():
            if len(failures) >= min_failures:
                error_msgs = [f["error_message"] for f in failures if f.get("error_message")]
                task_types = list(set(f["task_type"] for f in failures))

                content = f"Agent '{agent_type}' had {len(failures)} failures in the past {days} days. "
                content += f"Task types affected: {', '.join(task_types)}. "

                if error_msgs:
                    # Look for common patterns in error messages
                    common_errors = self._find_common_error_patterns(error_msgs)
                    if common_errors:
                        content += f"Common error: {common_errors}"

                confidence = min(0.5 + (len(failures) * 0.1), 0.9)

                insights.append({
                    "insight_type": "improvement",
                    "title": f"Failure pattern detected for {agent_type}",
                    "content": content,
                    "confidence": confidence
                })

        # Generate insights for specific task types with high failure rates
        for agent_task, failures in by_agent_task.items():
            if len(failures) >= 3:
                total_tasks = self._get_task_total(agent_task.split(":")[0], agent_task.split(":")[1], days)
                if total_tasks > 0:
                    failure_rate = len(failures) / total_tasks
                    if failure_rate > 0.5:
                        confidence = min(0.6 + failure_rate * 0.2, 0.95)
                        insights.append({
                            "insight_type": "pattern",
                            "title": f"High failure rate for task: {agent_task}",
                            "content": f"Task '{agent_task}' has a {failure_rate*100:.1f}% failure rate "
                                      f"({len(failures)} failures out of {total_tasks} attempts).",
                            "confidence": confidence
                        })

        return insights

    def analyze_project_health(self, stale_days: int = 30) -> List[Dict[str, Any]]:
        """Analyze project staleness and health."""
        insights = []
        projects = self.db.get_projects_summary()

        now = datetime.now()
        stale_projects = []

        for project in projects:
            try:
                if project.get("updated_at"):
                    updated = datetime.fromisoformat(project["updated_at"])
                    days_inactive = (now - updated).days

                    if days_inactive > stale_days:
                        stale_projects.append({
                            "name": project["project_name"],
                            "days": days_inactive,
                            "status": project.get("status", "unknown"),
                            "description": project.get("description", "")
                        })
            except (ValueError, TypeError, KeyError):
                pass

        if stale_projects:
            # Group by status
            by_status = defaultdict(list)
            for p in stale_projects:
                by_status[p["status"]].append(p)

            for status, projects_list in by_status.items():
                if status == "in_progress":
                    content = f"You have {len(projects_list)} in-progress projects that haven't been "
                    content += f"updated in over {stale_days} days: "
                    content += ", ".join([f"'{p['name']}' ({p['days']} days)" for p in projects_list[:3]])
                    if len(projects_list) > 3:
                        content += f" and {len(projects_list) - 3} more"
                    content += ". Consider completing or archiving these projects."

                    insights.append({
                        "insight_type": "suggestion",
                        "title": "Stale in-progress projects detected",
                        "content": content,
                        "confidence": min(0.5 + len(projects_list) * 0.05, 0.8)
                    })

        return insights

    def analyze_conversation_trends(self, days: int = 7) -> List[Dict[str, Any]]:
        """Analyze conversation patterns."""
        insights = []

        conversations = self.db.get_recent_conversations(limit=1000)
        cutoff = datetime.now() - timedelta(days=days)

        recent_by_agent = defaultdict(int)
        total_recent = 0

        for conv in conversations:
            try:
                if conv.get("timestamp"):
                    conv_time = datetime.fromisoformat(conv["timestamp"])
                    if conv_time >= cutoff:
                        recent_by_agent[conv["agent_type"]] += 1
                        total_recent += 1
            except (ValueError, TypeError):
                pass

        if total_recent == 0:
            return insights

        # Detect if certain agents are underutilized
        all_projects = self.db.get_projects_summary()
        active_projects = [p["project_name"] for p in all_projects if p.get("status") == "in_progress"]

        for agent_type, count in recent_by_agent.items():
            if count < 3 and len(active_projects) > 5:
                # This agent hasn't been very active
                insights.append({
                    "insight_type": "suggestion",
                    "title": f"Low activity from {agent_type}",
                    "content": f"Agent '{agent_type}' has only been involved in {count} conversations "
                              f"in the past {days} days. Consider if this agent type is still needed "
                              f"or if integrations need attention.",
                    "confidence": 0.5
                })

        return insights

    def _find_common_error_patterns(self, error_messages: List[str]) -> Optional[str]:
        """Find common patterns in error messages."""
        if not error_messages:
            return None

        # Simple approach: find the longest common prefix
        if len(error_messages) < 2:
            return error_messages[0][:100] if error_messages else None

        # Look for common keywords
        all_text = " ".join(error_messages).lower()

        common_patterns = [
            ("connection", "Connection-related errors"),
            ("timeout", "Timeout errors"),
            ("authentication", "Authentication failures"),
            ("permission", "Permission/authorization errors"),
            ("not found", "Resource not found errors"),
            ("invalid", "Invalid input/data errors"),
            ("network", "Network-related errors"),
        ]

        for keyword, pattern_name in common_patterns:
            if keyword in all_text:
                count = all_text.count(keyword)
                if count >= len(error_messages) * 0.5:
                    return pattern_name

        # Fall back to first error truncated
        return error_messages[0][:80] + "..." if error_messages[0] else None

    def _get_task_total(self, agent_type: str, task_type: str, days: int) -> int:
        """Get total task count for an agent/task combination."""
        logs = self.db.get_agent_logs(agent_type=agent_type, limit=500)
        cutoff = datetime.now() - timedelta(days=days)

        count = 0
        for log in logs:
            if log["task_type"] == task_type:
                try:
                    log_time = datetime.fromisoformat(log["timestamp"])
                    if log_time >= cutoff:
                        count += 1
                except (ValueError, TypeError):
                    pass

        return count

    def _extract_topics(self, conversations: List[Dict]) -> List[str]:
        """Extract topics from conversations using keyword analysis."""
        topics_found = set()
        text_content = " ".join(
            conv.get("content", "").lower() for conv in conversations
        )

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_content:
                    topics_found.add(topic)
                    break

        return list(topics_found)

    def _analyze_communication_style(self, conversations: List[Dict]) -> str:
        """Analyze user's communication style based on message patterns."""
        user_messages = [c for c in conversations if c.get("role") == "user"]
        if not user_messages:
            return "mixed"

        total_length = sum(len(c.get("content", "")) for c in user_messages)
        avg_length = total_length / len(user_messages) if user_messages else 0

        question_count = sum(1 for c in user_messages if "?" in c.get("content", ""))
        question_ratio = question_count / len(user_messages) if user_messages else 0

        if avg_length < 30 and question_ratio > 0.5:
            return "concise"
        elif avg_length > 200 and question_ratio < 0.3:
            return "detailed"
        else:
            return "mixed"

    def _analyze_active_hours(self, conversations: List[Dict]) -> Dict[str, bool]:
        """Analyze user's active hours from conversation timestamps."""
        hours = {"morning": False, "afternoon": False, "evening": False, "night": False}

        for conv in conversations:
            try:
                if conv.get("timestamp"):
                    conv_time = datetime.fromisoformat(conv["timestamp"])
                    hour = conv_time.hour
                    if 6 <= hour < 12:
                        hours["morning"] = True
                    elif 12 <= hour < 18:
                        hours["afternoon"] = True
                    elif 18 <= hour < 22:
                        hours["evening"] = True
                    else:
                        hours["night"] = True
            except (ValueError, TypeError):
                pass

        return hours

    def _detect_language(self, conversations: List[Dict]) -> str:
        """Simple Chinese/English detection."""
        user_messages = [c.get("content", "") for c in conversations if c.get("role") == "user"]
        if not user_messages:
            return "mixed"

        chinese_chars = 0
        total_chars = 0

        for content in user_messages:
            for char in content:
                if ord(char) > 127:
                    chinese_chars += 1
                total_chars += 1

        if total_chars == 0:
            return "mixed"

        chinese_ratio = chinese_chars / total_chars
        if chinese_ratio > 0.3:
            return "chinese"
        elif chinese_ratio < 0.1:
            return "english"
        else:
            return "mixed"

    def _detect_sentiment(self, conversations: List[Dict]) -> str:
        """Simple sentiment analysis (positive/neutral/negative)."""
        user_messages = [c.get("content", "").lower() for c in conversations if c.get("role") == "user"]
        if not user_messages:
            return "neutral"

        text = " ".join(user_messages)

        positive_count = sum(1 for word in self.POSITIVE_WORDS if word.lower() in text)
        negative_count = sum(1 for word in self.NEGATIVE_WORDS if word.lower() in text)

        if positive_count > negative_count + 2:
            return "positive"
        elif negative_count > positive_count + 2:
            return "negative"
        else:
            return "neutral"

    def build_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Build or update a user profile based on their conversations."""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)

        conversations = self.db.get_conversations_in_range(user_id, start_time, end_time)

        if not conversations:
            return {}

        profile_data = {
            "total_conversations": len(conversations),
            "interests": self._extract_topics(conversations),
            "communication_style": self._analyze_communication_style(conversations),
            "active_hours": self._analyze_active_hours(conversations),
            "language": self._detect_language(conversations),
            "sentiment": self._detect_sentiment(conversations)
        }

        # Determine preferred response length
        user_messages = [c for c in conversations if c.get("role") == "user"]
        if user_messages:
            avg_len = sum(len(c.get("content", "")) for c in user_messages) / len(user_messages)
            if avg_len < 50:
                profile_data["preferred_response_length"] = "short"
            elif avg_len > 300:
                profile_data["preferred_response_length"] = "long"
            else:
                profile_data["preferred_response_length"] = "medium"

        # Update in database
        self.db.upsert_user_profile(user_id, profile_data)

        return profile_data

    def get_user_daily_summary(self, user_id: str, summary_date: str = None) -> Dict[str, Any]:
        """Generate a daily summary for a user."""
        if summary_date is None:
            summary_date = datetime.now().strftime("%Y-%m-%d")

        # Get yesterday's date range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)

        conversations = self.db.get_conversations_in_range(user_id, start_time, end_time)

        if not conversations:
            return {"date": summary_date, "conversation_count": 0}

        user_messages = [c for c in conversations if c.get("role") == "user"]
        assistant_messages = [c for c in conversations if c.get("role") == "assistant"]

        total_length = sum(len(c.get("content", "")) for c in user_messages)
        avg_length = total_length / len(user_messages) if user_messages else 0

        agent_types = list(set(c.get("agent_type") for c in conversations if c.get("agent_type")))

        summary_data = {
            "conversation_count": len(conversations),
            "topics_discussed": self._extract_topics(conversations),
            "avg_conversation_length": round(avg_length, 1),
            "agent_types_interacted": agent_types,
            "dominant_sentiment": self._detect_sentiment(conversations),
            "summary_text": f"User had {len(conversations)} conversation(s) covering {len(agent_types)} agent type(s)."
        }

        self.db.upsert_daily_summary(user_id, summary_date, summary_data)

        return summary_data

    def _generate_user_profile_insights(self) -> List[Dict[str, Any]]:
        """Generate insights from user profiles."""
        insights = []

        profiles = self.db.get_all_user_profiles()
        for profile in profiles:
            user_id = profile.get("user_id")

            # Detect underutilized topics based on interests
            interests = profile.get("interests", [])
            if len(interests) == 0:
                continue

            # Suggest expanding topics if very narrow
            if len(interests) == 1:
                insights.append({
                    "insight_type": "suggestion",
                    "title": f"User {user_id} has narrow interests",
                    "content": f"User '{user_id}' only shows interest in {interests}. "
                              f"Consider introducing other topics to broaden their experience.",
                    "confidence": 0.5
                })

            # Analyze active hours for scheduling
            active_hours = profile.get("active_hours", {})
            if active_hours:
                true_hours = [k for k, v in active_hours.items() if v]
                if len(true_hours) == 1:
                    insights.append({
                        "insight_type": "pattern",
                        "title": f"User {user_id} has limited active hours",
                        "content": f"User '{user_id}' is only active during {true_hours[0]} time. "
                                  f"Best time to reach them: {true_hours[0]}.",
                        "confidence": 0.6
                    })

        return insights

    def generate_all_insights(self, confidence_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Generate all insights and store them in the database."""
        all_insights = []

        # Collect all types of insights
        all_insights.extend(self.analyze_failure_patterns())
        all_insights.extend(self.analyze_project_health())
        all_insights.extend(self.analyze_conversation_trends())
        all_insights.extend(self._generate_user_profile_insights())

        # Sort by confidence and store the best ones
        all_insights.sort(key=lambda x: x["confidence"], reverse=True)

        stored_insights = []
        for insight in all_insights:
            if insight["confidence"] >= confidence_threshold:
                insight_id = self.db.record_insight(
                    insight_type=insight["insight_type"],
                    title=insight["title"],
                    content=insight["content"],
                    confidence=insight["confidence"]
                )
                insight["id"] = insight_id
                stored_insights.append(insight)

        return stored_insights
