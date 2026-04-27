"""
Daily Routine Manager - Manages recurring daily routines
"""
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
from database import get_db
from models import DailyRoutine


class RoutineManager:
    """Manages daily routines"""

    def __init__(self):
        self.db = get_db()

    def create_routine(self, title: str, time_of_day: time,
                       days_of_week: List[int] = None, duration_minutes: int = 60,
                       description: str = '') -> DailyRoutine:
        """Create a new daily routine"""
        if days_of_week is None:
            days_of_week = [1, 2, 3, 4, 5]  # Weekdays by default

        routine_id = self.db.create_routine(
            title=title,
            time_of_day=time_of_day.isoformat(),
            days_of_week=days_of_week,
            duration_minutes=duration_minutes,
            description=description
        )
        return self.get_routine(routine_id)

    def get_routine(self, routine_id: int) -> Optional[DailyRoutine]:
        """Get a routine by ID"""
        data = self.db.get_routine(routine_id)
        return DailyRoutine.from_dict(data) if data else None

    def get_routines(self, is_active: Optional[bool] = None) -> List[DailyRoutine]:
        """Get all routines"""
        data_list = self.db.get_routines(is_active=is_active)
        return [DailyRoutine.from_dict(d) for d in data_list]

    def get_routines_for_today(self) -> List[DailyRoutine]:
        """Get routines for today (1=Monday, 7=Sunday)"""
        today = datetime.now().weekday() + 1  # Convert to 1-7
        data_list = self.db.get_routines_for_day(today)
        return [DailyRoutine.from_dict(d) for d in data_list]

    def update_routine(self, routine_id: int, **kwargs) -> bool:
        """Update a routine"""
        if 'time_of_day' in kwargs and kwargs['time_of_day']:
            kwargs['time_of_day'] = kwargs['time_of_day'].isoformat()
        if 'is_active' in kwargs and kwargs['is_active'] is not None:
            kwargs['is_active'] = bool(kwargs['is_active'])

        return self.db.update_routine(routine_id, **kwargs)

    def toggle_routine(self, routine_id: int) -> bool:
        """Toggle routine active status"""
        routine = self.get_routine(routine_id)
        if routine:
            return self.update_routine(routine_id, is_active=not routine.is_active)
        return False

    def delete_routine(self, routine_id: int) -> bool:
        """Delete a routine"""
        return self.db.delete_routine(routine_id)

    def trigger_routine(self, routine_id: int, target_date: date = None) -> Dict[str, Any]:
        """Trigger a routine to create a schedule for today or a specific date"""
        from schedule_manager import get_schedule_manager

        routine = self.get_routine(routine_id)
        if not routine:
            return {'success': False, 'message': 'Routine not found'}

        if target_date is None:
            target_date = date.today()

        # Calculate start and end time
        start_dt = datetime.combine(target_date, routine.time_of_day)
        end_dt = start_dt + timedelta(minutes=routine.duration_minutes)

        # Create schedule
        manager = get_schedule_manager()
        schedule = manager.create_schedule(
            date=target_date,
            start_time=routine.time_of_day,
            end_time=end_dt.time(),
            task_id=None,
            slot_type='routine'
        )

        return {
            'success': True,
            'schedule_id': schedule.id,
            'message': f'Routine "{routine.title}" scheduled for {target_date}'
        }

    def trigger_all_routines_for_today(self) -> List[Dict[str, Any]]:
        """Trigger all active routines for today"""
        routines = self.get_routines_for_today()
        results = []
        for routine in routines:
            result = self.trigger_routine(routine.id)
            results.append(result)
        return results

    def get_routine_summary(self) -> Dict[str, Any]:
        """Get summary of all routines"""
        all_routines = self.get_routines()
        today_routines = self.get_routines_for_today()

        # Group by time of day
        time_slots = {}
        for routine in today_routines:
            slot = routine.time_of_day.strftime("%H:%M") if routine.time_of_day else "Unknown"
            if slot not in time_slots:
                time_slots[slot] = []
            time_slots[slot].append(routine.to_dict())

        return {
            'total_routines': len(all_routines),
            'active_routines': len([r for r in all_routines if r.is_active]),
            'today_routines_count': len(today_routines),
            'today_by_time': time_slots
        }


# Singleton instance
_routine_manager_instance: Optional[RoutineManager] = None


def get_routine_manager() -> RoutineManager:
    """Get routine manager singleton"""
    global _routine_manager_instance
    if _routine_manager_instance is None:
        _routine_manager_instance = RoutineManager()
    return _routine_manager_instance
