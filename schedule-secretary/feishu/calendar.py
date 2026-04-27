"""
Feishu Calendar Integration
Provides bidirectional sync between local schedules and Feishu Calendar
"""
import os
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeishuCalendar:
    """Feishu Calendar API integration"""

    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.base_url = "https://open.feishu.cn/open-apis"

    def _get_access_token(self) -> str:
        """Get tenant access token"""
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        if result.get("code") == 0:
            return result.get("tenant_access_token")
        else:
            raise Exception(f"Failed to get access token: {result}")

    def _get_primary_calendar_id(self) -> str:
        """Get user's primary calendar ID"""
        token = self._get_access_token()
        url = f"{self.base_url}/calendar/v4/calendars/primary"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers)
        result = response.json()

        if result.get("code") == 0:
            return result.get("calendar", {}).get("calendar_id", "")
        else:
            logger.error(f"Failed to get primary calendar: {result}")
            return ""

    def get_events(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get calendar events within time range"""
        try:
            token = self._get_access_token()
            calendar_id = self._get_primary_calendar_id()

            if not calendar_id:
                return []

            url = f"{self.base_url}/calendar/v4/calendars/{calendar_id}/events"
            headers = {"Authorization": f"Bearer {token}"}
            params = {
                "start_time": int(start_time.timestamp()),
                "end_time": int(end_time.timestamp()),
                "page_size": 100
            }

            response = requests.get(url, headers=headers, params=params)
            result = response.json()

            if result.get("code") == 0:
                events = result.get("items", [])
                return [self._parse_feishu_event(e) for e in events]
            else:
                logger.error(f"Failed to get events: {result}")
                return []

        except Exception as e:
            logger.error(f"Error getting Feishu events: {e}")
            return []

    def get_today_events(self) -> List[Dict]:
        """Get today's calendar events"""
        today = date.today()
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
        return self.get_events(start, end)

    def get_week_events(self) -> List[Dict]:
        """Get this week's calendar events"""
        today = date.today()
        start = datetime.combine(today, time.min)
        end = datetime.combine(today + timedelta(days=7), time.max)
        return self.get_events(start, end)

    def _parse_feishu_event(self, event: Dict) -> Dict:
        """Parse Feishu event to local format"""
        start_dt = event.get("start_time", "")
        end_dt = event.get("end_time", "")

        # Parse start time
        try:
            start_time = datetime.fromtimestamp(int(start_dt))
        except:
            start_time = datetime.now()

        # Parse end time
        try:
            end_time = datetime.fromtimestamp(int(end_dt))
        except:
            end_time = start_time + timedelta(hours=1)

        # Determine event type based on title/description
        title = event.get("summary", "无标题")
        description = event.get("description", "")

        slot_type = "task"
        if any(kw in title for kw in ["会议", "meeting", "会", "讨论"]):
            slot_type = "meeting"
        elif any(kw in title for kw in ["休息", "break", "午饭", "午餐"]):
            slot_type = "break"

        return {
            'feishu_event_id': event.get("event_id", ""),
            'title': title,
            'description': description,
            'start_time': start_time,
            'end_time': end_time,
            'slot_type': slot_type,
            'status': 'done' if event.get("status") == "confirmed" else 'scheduled',
            'location': event.get("location", {}).get("name", ""),
            'attendees_count': len(event.get("attendees", []))
        }

    def create_event(self, title: str, start_time: datetime, end_time: datetime,
                    description: str = "", location: str = "") -> Optional[str]:
        """Create a calendar event in Feishu"""
        try:
            token = self._get_access_token()
            calendar_id = self._get_primary_calendar_id()

            if not calendar_id:
                return None

            url = f"{self.base_url}/calendar/v4/calendars/{calendar_id}/events"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            data = {
                "summary": title,
                "description": description,
                "start_time": {
                    "timestamp": str(int(start_time.timestamp())),
                    "timezone": "Asia/Shanghai"
                },
                "end_time": {
                    "timestamp": str(int(end_time.timestamp())),
                    "timezone": "Asia/Shanghai"
                }
            }

            if location:
                data["location"] = {
                    "name": location
                }

            response = requests.post(url, headers=headers, json=data)
            result = response.json()

            if result.get("code") == 0:
                event_id = result.get("event", {}).get("event_id", "")
                logger.info(f"Created Feishu event: {event_id}")
                return event_id
            else:
                logger.error(f"Failed to create event: {result}")
                return None

        except Exception as e:
            logger.error(f"Error creating Feishu event: {e}")
            return None

    def update_event(self, event_id: str, title: str = None,
                    start_time: datetime = None, end_time: datetime = None,
                    description: str = None) -> bool:
        """Update a calendar event in Feishu"""
        try:
            token = self._get_access_token()
            calendar_id = self._get_primary_calendar_id()

            if not calendar_id:
                return False

            url = f"{self.base_url}/calendar/v4/calendars/{calendar_id}/events/{event_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            update_data = {}
            if title:
                update_data["summary"] = title
            if description:
                update_data["description"] = description
            if start_time:
                update_data["start_time"] = {
                    "timestamp": str(int(start_time.timestamp())),
                    "timezone": "Asia/Shanghai"
                }
            if end_time:
                update_data["end_time"] = {
                    "timestamp": str(int(end_time.timestamp())),
                    "timezone": "Asia/Shanghai"
                }

            if not update_data:
                return False

            response = requests.patch(url, headers=headers, json=update_data)
            result = response.json()

            if result.get("code") == 0:
                logger.info(f"Updated Feishu event: {event_id}")
                return True
            else:
                logger.error(f"Failed to update event: {result}")
                return False

        except Exception as e:
            logger.error(f"Error updating Feishu event: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event from Feishu"""
        try:
            token = self._get_access_token()
            calendar_id = self._get_primary_calendar_id()

            if not calendar_id:
                return False

            url = f"{self.base_url}/calendar/v4/calendars/{calendar_id}/events/{event_id}"
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.delete(url, headers=headers)
            result = response.json()

            if result.get("code") == 0:
                logger.info(f"Deleted Feishu event: {event_id}")
                return True
            else:
                logger.error(f"Failed to delete event: {result}")
                return False

        except Exception as e:
            logger.error(f"Error deleting Feishu event: {e}")
            return False


class CalendarSync:
    """Bidirectional sync between local schedules and Feishu Calendar"""

    def __init__(self):
        self.feishu_calendar = FeishuCalendar()

    def sync_to_feishu(self, schedule) -> Optional[str]:
        """Sync a local schedule event to Feishu Calendar"""
        if not schedule.start_time or not schedule.date:
            return None

        start_dt = datetime.combine(schedule.date, schedule.start_time)
        end_dt = datetime.combine(
            schedule.date,
            schedule.end_time if schedule.end_time else (schedule.start_time + timedelta(hours=1))
        )

        title = schedule.task_title or (
            schedule.slot_type.value if hasattr(schedule.slot_type, 'value') else schedule.slot_type
        )

        return self.feishu_calendar.create_event(
            title=title,
            start_time=start_dt,
            end_time=end_dt,
            description=schedule.task_description or ""
        )

    def sync_from_feishu(self) -> List[Dict]:
        """Sync events from Feishu Calendar to local"""
        events = self.feishu_calendar.get_today_events()
        return events

    def sync_all_to_feishu(self) -> int:
        """Sync all local schedules to Feishu Calendar"""
        from schedule_manager import get_schedule_manager
        from database import get_db

        manager = get_schedule_manager()
        db = get_db()

        today = date.today()
        schedules = manager.get_schedules_with_tasks(today)

        synced_count = 0
        for schedule in schedules:
            if schedule.status == 'scheduled' and schedule.start_time:
                event_id = self.sync_to_feishu(schedule)
                if event_id:
                    # Store mapping
                    synced_count += 1

        return synced_count


# Singleton instance
_calendar_instance: Optional[FeishuCalendar] = None
_sync_instance: Optional[CalendarSync] = None


def get_feishu_calendar() -> FeishuCalendar:
    """Get Feishu calendar singleton"""
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = FeishuCalendar()
    return _calendar_instance


def get_calendar_sync() -> CalendarSync:
    """Get calendar sync singleton"""
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = CalendarSync()
    return _sync_instance