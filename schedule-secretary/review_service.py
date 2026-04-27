"""
AI Review Service - Daily Review Conversation Handler
Provides multi-turn AI conversation for daily work review
"""
import os
import json
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from config import Config
from database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReviewService:
    """Handles AI daily review conversations"""

    def __init__(self):
        self.db = get_db()
        self.claude_api_key = Config.CLAUDE_API_KEY

    def start_review(self, user_open_id: str = None) -> Dict[str, Any]:
        """Start a new review session for today"""
        today = date.today()

        # Check if review already exists for today
        existing = self.db.get_review_by_date(today)

        if existing and existing.get('completed'):
            return {
                'success': False,
                'message': '今日复盘已完成'
            }

        # Create or get review entry
        if not existing:
            review_id = self.db.create_review(review_date=today)
            review = self.db.get_review(review_id)
        else:
            review = existing

        # Build initial context
        context = self._build_initial_context()

        return {
            'success': True,
            'review_id': review.get('id') if review else None,
            'message': context.get('welcome_message'),
            'context': context
        }

    def process_review_response(self, user_input: str, user_open_id: str = None) -> Dict[str, Any]:
        """Process user input during review conversation"""
        today = date.today()
        review = self.db.get_review_by_date(today)

        if not review:
            return self.start_review(user_open_id)

        review_id = review.get('id')

        # Update conversation context
        existing_context = review.get('conversation_context', '')
        if existing_context:
            try:
                context_data = json.loads(existing_context)
            except:
                context_data = {'messages': []}
        else:
            context_data = {'messages': []}

        # Add user message
        context_data['messages'].append({
            'role': 'user',
            'content': user_input,
            'time': datetime.now().isoformat()
        })

        # Get AI response
        ai_response = self._get_ai_review_response(context_data['messages'])

        # Add AI response
        context_data['messages'].append({
            'role': 'assistant',
            'content': ai_response.get('message'),
            'time': datetime.now().isoformat()
        })

        # Save updated context
        self.db.update_review(review_id, conversation_context=json.dumps(context_data, ensure_ascii=False))

        # Check if review is complete
        is_complete = ai_response.get('is_complete', False)

        if is_complete:
            # Extract summary and suggestions
            self.db.update_review(
                review_id,
                completed=1,
                summary=ai_response.get('summary', ''),
                suggestions=ai_response.get('suggestions', '')
            )

        return {
            'success': True,
            'review_id': review_id,
            'message': ai_response.get('message'),
            'is_complete': is_complete,
            'summary': ai_response.get('summary', '') if is_complete else None,
            'suggestions': ai_response.get('suggestions', '') if is_complete else None
        }

    def _build_initial_context(self) -> Dict[str, Any]:
        """Build initial review context with today's data"""
        from schedule_manager import get_schedule_manager

        manager = get_schedule_manager()
        today = date.today()

        # Get today's schedules
        schedules = manager.get_schedules_with_tasks(today)
        completed = [s for s in schedules if s.status == 'done']
        missed = [s for s in schedules if s.status == 'missed']
        pending = [s for s in schedules if s.status == 'scheduled']

        # Get tasks
        pending_tasks = manager.get_pending_tasks()

        # Format schedules for prompt
        schedule_summary = f"今日日程: {len(schedules)}项, 完成: {len(completed)}项"
        if pending:
            schedule_summary += f", 进行中: {len(pending)}项"
        if missed:
            schedule_summary += f", 错过: {len(missed)}项"

        task_summary = f"待办任务: {len(pending_tasks)}项"
        if pending_tasks:
            task_titles = [t.title for t in pending_tasks[:5]]
            task_summary += f" ({', '.join(task_titles)})"

        welcome_message = (
            f"🌙 今日工作复盘\n\n"
            f"让我帮你回顾一下今天的工作情况...\n\n"
            f"{schedule_summary}\n"
            f"{task_summary}\n\n"
            f"📝 请分享：\n"
            f"1. 今天完成了哪些工作？\n"
            f"2. 有哪些事情没完成？\n"
            f"3. 遇到什么困难了吗？\n\n"
            f"我会帮你分析并给出建议 📝"
        )

        return {
            'welcome_message': welcome_message,
            'schedule_summary': schedule_summary,
            'task_summary': task_summary,
            'completed_count': len(completed),
            'missed_count': len(missed),
            'pending_count': len(pending),
            'pending_tasks': [t.to_dict() if hasattr(t, 'to_dict') else t for t in pending_tasks[:10]]
        }

    def _get_ai_review_response(self, messages: List[Dict]) -> Dict[str, Any]:
        """Get AI response using Claude API"""
        if not self.claude_api_key:
            return self._get_fallback_response(messages)

        try:
            import requests

            # Build conversation for Claude
            conversation = []

            # System prompt
            system_prompt = (
                "你是一个工作复盘助手，帮助用户回顾一天的工作情况。\n"
                "请通过多轮对话引导用户完成每日复盘。\n"
                "复盘维度包括：\n"
                "1. 今日完成的任务\n"
                "2. 未完成的任务及原因\n"
                "3. 时间使用效率分析\n"
                "4. 明天的改进建议\n\n"
                "每次回复要简洁（不超过100字），多提问引导用户提供信息。\n"
                "当收集到足够信息后，给出总结和建议。\n"
                "用中文交流。"
            )

            for msg in messages:
                conversation.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', '')
                })

            # Call Claude API
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.claude_api_key,
                "anthropic-version": "2023-06-01",
                "anthropic-dangerous-direct-browser-access": "true"
            }

            data = {
                "model": "claude-opus-4-6",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": conversation
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)
            result = response.json()

            if response.status_code == 200 and result.get('content'):
                ai_message = result['content'][0].get('text', '')
                is_complete = '总结' in ai_message or '建议' in ai_message
                return {
                    'message': ai_message,
                    'is_complete': is_complete,
                    'summary': ai_message if is_complete else None,
                    'suggestions': None
                }
            else:
                logger.error(f"Claude API error: {result}")
                return self._get_fallback_response(messages)

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return self._get_fallback_response(messages)

    def _get_fallback_response(self, messages: List[Dict]) -> Dict[str, Any]:
        """Fallback response when Claude API is not available"""
        user_inputs = [m['content'] for m in messages if m.get('role') == 'user']

        if len(user_inputs) == 1:
            return {
                'message': '好的，请继续分享... 还有哪些方面想回顾的吗？',
                'is_complete': False,
                'summary': None,
                'suggestions': None
            }
        elif len(user_inputs) == 2:
            return {
                'message': '明白了！最后一个问题：明天有什么需要改进的地方吗？',
                'is_complete': False,
                'summary': None,
                'suggestions': None
            }
        else:
            return {
                'message': (
                    '📋 今日复盘总结：\n\n'
                    '感谢你的分享！\n\n'
                    '💡 建议：\n'
                    '1. 明天继续跟进未完成的任务\n'
                    '2. 注意合理安排时间\n'
                    '3. 重要的事情优先处理\n\n'
                    '复盘已完成，明天加油！💪'
                ),
                'is_complete': True,
                'summary': '用户完成了今日工作复盘',
                'suggestions': '明天继续跟进未完成任务，合理安排时间'
            }

    def get_review_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Get review history"""
        return self.db.get_reviews(limit=limit)

    def get_review_by_date(self, review_date: date) -> Optional[Dict[str, Any]]:
        """Get review for specific date"""
        return self.db.get_review_by_date(review_date)


# Singleton instance
_review_service_instance: Optional[ReviewService] = None


def get_review_service() -> ReviewService:
    """Get review service singleton"""
    global _review_service_instance
    if _review_service_instance is None:
        _review_service_instance = ReviewService()
    return _review_service_instance