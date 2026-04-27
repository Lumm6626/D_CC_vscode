"""
Reminder Service - APScheduler-based reminder and notification service
"""
import os
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import Config
from schedule_manager import get_schedule_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReminderService:
    """Manages scheduled reminders using APScheduler"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self._setup_jobs()

    def _setup_jobs(self):
        """Setup scheduled jobs"""
        # Check for upcoming reminders every minute
        self.scheduler.add_job(
            func=self._check_reminders,
            trigger=IntervalTrigger(minutes=Config.REMINDER_CHECK_INTERVAL_MINUTES),
            id='reminder_check',
            name='Check upcoming reminders',
            replace_existing=True
        )

        # Morning summary at 8:30 AM (every day including weekends)
        self.scheduler.add_job(
            func=self._send_morning_summary,
            trigger=CronTrigger(hour=8, minute=30, day_of_week='0-6'),
            id='morning_summary',
            name='Send morning summary at 8:30',
            replace_existing=True
        )

        # Email check - morning at 7:00
        self.scheduler.add_job(
            func=self._check_emails_morning,
            trigger=CronTrigger(hour=7, minute=0, day_of_week='0-6'),
            id='email_check_morning',
            name='Check emails morning',
            replace_existing=True
        )

        # Email check - midday at 12:00
        self.scheduler.add_job(
            func=self._check_emails_midday,
            trigger=CronTrigger(hour=12, minute=0, day_of_week='0-6'),
            id='email_check_midday',
            name='Check emails midday',
            replace_existing=True
        )

        # Email check - evening at 17:00
        self.scheduler.add_job(
            func=self._check_emails_evening,
            trigger=CronTrigger(hour=17, minute=0, day_of_week='0-6'),
            id='email_check_evening',
            name='Check emails evening',
            replace_existing=True
        )

        # AI daily review at 17:20 (every day including weekends)
        self.scheduler.add_job(
            func=self._trigger_ai_review,
            trigger=CronTrigger(hour=17, minute=20, day_of_week='0-6'),
            id='ai_daily_review',
            name='AI daily review at 17:20',
            replace_existing=True
        )

    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Reminder service started")

    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Reminder service stopped")

    def _check_reminders(self):
        """Check for upcoming reminders and send notifications"""
        try:
            from feishu.bot import send_text_message

            manager = get_schedule_manager()
            now = datetime.now()
            today = now.date()

            # Get today's schedules
            schedules = manager.get_schedules_with_tasks(today)

            for schedule in schedules:
                if schedule.status == 'scheduled' and schedule.start_time:
                    schedule_dt = datetime.combine(today, schedule.start_time)

                    # Check if within reminder window (15 minutes before)
                    diff = (schedule_dt - now).total_seconds() / 60

                    if 0 < diff <= Config.REMINDER_CHECK_INTERVAL_MINUTES:
                        # Send reminder
                        if schedule.task_title:
                            message = (
                                f"提醒：{schedule.task_title}\n"
                                f"时间：{schedule.start_time.strftime('%H:%M')}"
                            )
                        else:
                            message = (
                                f"提醒：{schedule.slot_type.value if hasattr(schedule.slot_type, 'value') else schedule.slot_type}\n"
                                f"时间：{schedule.start_time.strftime('%H:%M')}"
                            )

                        try:
                            send_text_message(message)
                            logger.info(f"Sent reminder for schedule {schedule.id}")
                        except Exception as e:
                            logger.error(f"Failed to send reminder: {e}")

        except Exception as e:
            logger.error(f"Error checking reminders: {e}")

    def _send_morning_summary(self):
        """Send morning summary at 8:30 with enhanced content"""
        try:
            from feishu.bot import send_text_message
            from routine_manager import get_routine_manager

            manager = get_schedule_manager()
            routine_mgr = get_routine_manager()

            today = date.today()
            schedules = manager.get_today_schedules()
            routines = routine_mgr.get_routines_for_today()

            # Sort schedules by start time
            sorted_schedules = sorted(
                [s for s in schedules if s.start_time],
                key=lambda s: s.start_time
            )

            # Count pending tasks
            pending_tasks = manager.get_pending_tasks()
            high_priority = [t for t in pending_tasks if (t.priority.value if hasattr(t.priority, 'value') else t.priority) == 'high']

            # Get pending reply emails
            try:
                from email_task_extractor import get_pending_reply_emails, format_pending_emails_message
                pending_emails = get_pending_reply_emails(max_count=20)
                email_count = len(pending_emails)
            except Exception as e:
                logger.error(f"Error getting pending emails: {e}")
                pending_emails = []
                email_count = 0

            # Build message
            day_name = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][today.weekday()]
            is_weekend = today.weekday() >= 5

            message = (
                f"☀️ 早安！{today.strftime('%m月%d日')} {day_name}\n"
                f"{'周末愉快' if is_weekend else '新的一天开始啦'}\n\n"
            )

            # Today's schedule
            if sorted_schedules:
                message += f"📅 今日日程 ({len(sorted_schedules)}项):\n"
                for s in sorted_schedules[:5]:
                    time_str = s.start_time.strftime('%H:%M') if hasattr(s.start_time, 'strftime') else s.start_time[:5]
                    title = s.task_title or (s.slot_type.value if hasattr(s.slot_type, 'value') else s.slot_type)
                    message += f"  ⏰ {time_str} {title}\n"
            else:
                message += "📅 今日暂无日程安排\n"

            # Pending reply emails
            message += f"\n📧 待回复邮件: {email_count}封"
            if pending_emails:
                for email in pending_emails[:3]:
                    message += f"\n  • [{email['sender_name']}] {email['subject'][:20]}..."

            # Pending tasks
            message += f"\n📋 待办任务: {len(pending_tasks)}项"
            if high_priority:
                message += f" (其中{len(high_priority)}项紧急)"
                for t in high_priority[:2]:
                    message += f"\n  🔴 {t.title[:25]}..."

            # Routines
            if routines:
                message += f"\n🔄 日常任务: {len(routines)}项"

            try:
                send_text_message(message)
                logger.info("Sent morning summary at 8:30")
            except Exception as e:
                logger.error(f"Failed to send morning summary: {e}")

        except Exception as e:
            logger.error(f"Error sending morning summary: {e}")

    def _check_emails_morning(self):
        """Check emails in the morning and send summary"""
        try:
            from feishu.bot import send_text_message
            from email_task_extractor import get_pending_reply_emails, format_pending_emails_message

            pending_emails = get_pending_reply_emails(max_count=20)
            message = format_pending_emails_message(pending_emails)

            send_text_message(message)
            logger.info("Sent morning email check")

        except Exception as e:
            logger.error(f"Error in morning email check: {e}")

    def _check_emails_midday(self):
        """Check emails at midday"""
        try:
            from feishu.bot import send_text_message
            from email_task_extractor import get_pending_reply_emails

            pending_emails = get_pending_reply_emails(max_count=20)
            if pending_emails:
                message = f"📧 午间邮件提醒\n\n还有{len(pending_emails)}封邮件待回复"
                send_text_message(message)

            logger.info("Sent midday email check")

        except Exception as e:
            logger.error(f"Error in midday email check: {e}")

    def _check_emails_evening(self):
        """Check emails in the evening"""
        try:
            from feishu.bot import send_text_message
            from email_task_extractor import get_pending_reply_emails

            pending_emails = get_pending_reply_emails(max_count=20)
            if pending_emails:
                message = f"📧 晚间邮件提醒\n\n还有{len(pending_emails)}封邮件待回复，别忘了处理哦"
                send_text_message(message)

            logger.info("Sent evening email check")

        except Exception as e:
            logger.error(f"Error in evening email check: {e}")

    def _trigger_ai_review(self):
        """Trigger AI daily review at 17:20"""
        try:
            from feishu.bot import send_text_message

            today = date.today()
            message = (
                f"🌙 今日工作复盘时间到！\n\n"
                f"让我帮你回顾一下今天的工作情况...\n\n"
                f"请告诉我：\n"
                f"1. 今天完成了哪些工作？\n"
                f"2. 有哪些事情没完成？\n"
                f"3. 遇到什么困难了吗？\n\n"
                f"输入你的回答，我会帮你分析并给出建议 📝"
            )

            send_text_message(message)
            logger.info("Triggered AI daily review at 17:20")

            # Initialize review session in database
            try:
                from database import get_db
                db = get_db()
                existing = db.get_review_by_date(today)
                if not existing:
                    db.create_review(review_date=today)
            except Exception as e:
                logger.error(f"Error initializing review: {e}")

        except Exception as e:
            logger.error(f"Error triggering AI review: {e}")

    def _send_evening_summary(self):
        """Send evening summary"""
        try:
            from feishu.bot import send_text_message

            manager = get_schedule_manager()
            today = date.today()

            schedules = manager.get_schedules_with_tasks(today)
            completed = [s for s in schedules if s.status == 'done']
            missed = [s for s in schedules if s.status == 'missed']

            message = (
                f"🌙 今日完成情况\n"
                f"日期：{today.strftime('%Y年%m月%d日')}\n"
                f"完成：{len(completed)}/{len(schedules)}项日程\n"
            )

            if missed:
                message += f"错过：{len(missed)}项\n"

            pending = manager.get_pending_tasks()
            if pending:
                message += f"\n还有{len(pending)}项待办未完成"

            try:
                send_text_message(message)
                logger.info("Sent evening summary")
            except Exception as e:
                logger.error(f"Failed to send evening summary: {e}")

        except Exception as e:
            logger.error(f"Error sending evening summary: {e}")

    def send_reminder_now(self, schedule_id: int) -> bool:
        """Send immediate reminder for a specific schedule"""
        try:
            from feishu.bot import send_text_message

            manager = get_schedule_manager()
            schedule = manager.get_schedule(schedule_id)

            if not schedule:
                return False

            if schedule.task_title:
                message = f"提醒：{schedule.task_title}"
            else:
                message = f"提醒：{schedule.slot_type}"

            send_text_message(message)
            return True

        except Exception as e:
            logger.error(f"Failed to send immediate reminder: {e}")
            return False

    def get_job_status(self) -> List[Dict[str, Any]]:
        """Get status of scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        return [
            {
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]


# Singleton instance
_reminder_service_instance: Optional[ReminderService] = None


def get_reminder_service() -> ReminderService:
    """Get reminder service singleton"""
    global _reminder_service_instance
    if _reminder_service_instance is None:
        _reminder_service_instance = ReminderService()
    return _reminder_service_instance
