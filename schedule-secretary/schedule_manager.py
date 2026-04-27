"""
Schedule Manager - Task pool and schedule management
"""
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
from database import get_db
from models import Task, Schedule, TaskSource, TaskPriority, TaskStatus, SlotType, ScheduleStatus


class ScheduleManager:
    """Manages tasks and schedules"""

    def __init__(self):
        self.db = get_db()

    # ==================== Task Operations ====================

    def create_task(self, title: str, description: str = '', source: str = 'manual',
                   priority: str = 'normal', due_date: Optional[date] = None,
                   estimated_hours: Optional[float] = None) -> Task:
        """Create a new task"""
        task_id = self.db.create_task(
            title=title,
            description=description,
            source=source,
            priority=priority,
            due_date=due_date.isoformat() if due_date else None,
            estimated_hours=estimated_hours
        )
        return self.get_task(task_id)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID"""
        data = self.db.get_task(task_id)
        return Task.from_dict(data) if data else None

    def get_tasks(self, status: Optional[str] = None, source: Optional[str] = None,
                  priority: Optional[str] = None) -> List[Task]:
        """Get tasks with filters"""
        data_list = self.db.get_tasks(status=status, source=source, priority=priority)
        return [Task.from_dict(d) for d in data_list]

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks"""
        return self.get_tasks(status='pending')

    def update_task(self, task_id: int, **kwargs) -> bool:
        """Update a task"""
        # Convert enums to values if needed
        if 'priority' in kwargs and hasattr(kwargs['priority'], 'value'):
            kwargs['priority'] = kwargs['priority'].value
        if 'status' in kwargs and hasattr(kwargs['status'], 'value'):
            kwargs['status'] = kwargs['status'].value
        if 'source' in kwargs and hasattr(kwargs['source'], 'value'):
            kwargs['source'] = kwargs['source'].value

        if 'due_date' in kwargs and kwargs['due_date']:
            kwargs['due_date'] = kwargs['due_date'].isoformat()

        return self.db.update_task(task_id, **kwargs)

    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed"""
        return self.update_task(task_id, status='completed')

    def delete_task(self, task_id: int) -> bool:
        """Delete a task"""
        return self.db.delete_task(task_id)

    # ==================== Schedule Operations ====================

    def create_schedule(self, date: date, start_time: Optional[time] = None,
                       end_time: Optional[time] = None, task_id: Optional[int] = None,
                       slot_type: str = 'task') -> Schedule:
        """Create a new schedule entry"""
        schedule_id = self.db.create_schedule(
            date=date.isoformat(),
            start_time=start_time.isoformat() if start_time else None,
            end_time=end_time.isoformat() if end_time else None,
            task_id=task_id,
            slot_type=slot_type
        )
        return self.get_schedule(schedule_id)

    def get_schedule(self, schedule_id: int) -> Optional[Schedule]:
        """Get a schedule by ID"""
        data = self.db.get_schedule(schedule_id)
        return Schedule.from_dict(data) if data else None

    def get_schedules(self, target_date: Optional[date] = None,
                      status: Optional[str] = None,
                      slot_type: Optional[str] = None) -> List[Schedule]:
        """Get schedules with filters"""
        data_list = self.db.get_schedules(
            date=target_date.isoformat() if target_date else None,
            status=status,
            slot_type=slot_type
        )
        return [Schedule.from_dict(d) for d in data_list]

    def get_schedules_with_tasks(self, target_date: Optional[date] = None) -> List[Schedule]:
        """Get schedules with joined task data"""
        data_list = self.db.get_schedules_with_tasks(
            date=target_date.isoformat() if target_date else None
        )
        return [Schedule.from_dict(d) for d in data_list]

    def get_today_schedules(self) -> List[Schedule]:
        """Get today's schedules"""
        return self.get_schedules_with_tasks(target_date=date.today())

    def update_schedule(self, schedule_id: int, **kwargs) -> bool:
        """Update a schedule"""
        if 'slot_type' in kwargs and hasattr(kwargs['slot_type'], 'value'):
            kwargs['slot_type'] = kwargs['slot_type'].value
        if 'status' in kwargs and hasattr(kwargs['status'], 'value'):
            kwargs['status'] = kwargs['status'].value

        if 'date' in kwargs and kwargs['date']:
            kwargs['date'] = kwargs['date'].isoformat()
        if 'start_time' in kwargs and kwargs['start_time']:
            kwargs['start_time'] = kwargs['start_time'].isoformat()
        if 'end_time' in kwargs and kwargs['end_time']:
            kwargs['end_time'] = kwargs['end_time'].isoformat()

        return self.db.update_schedule(schedule_id, **kwargs)

    def mark_schedule_done(self, schedule_id: int) -> bool:
        """Mark a schedule as done"""
        return self.update_schedule(schedule_id, status='done')

    def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule"""
        return self.db.delete_schedule(schedule_id)

    # ==================== Time Slot Management ====================

    def get_available_slots(self, target_date: date,
                           start_hour: int = 9,
                           end_hour: int = 18) -> List[Dict[str, Any]]:
        """Get available time slots for a given date"""
        schedules = self.get_schedules(target_date)

        # Create occupied slots set
        occupied = set()
        for s in schedules:
            if s.start_time and s.end_time:
                occupied.add((s.start_time, s.end_time))

        # Generate available slots (1 hour each)
        available = []
        for hour in range(start_hour, end_hour):
            slot_start = time(hour, 0)
            slot_end = time(hour + 1, 0)

            # Check if slot conflicts with any scheduled item
            is_available = True
            for occ_start, occ_end in occupied:
                if not (slot_end <= occ_start or slot_start >= occ_end):
                    is_available = False
                    break

            if is_available:
                available.append({
                    'start_time': slot_start.isoformat(),
                    'end_time': slot_end.isoformat(),
                    'hour': hour
                })

        return available

    def schedule_task(self, task_id: int, target_date: date,
                     start_time: time, end_time: time) -> Optional[Schedule]:
        """Schedule a task at a specific time"""
        # Verify task exists
        task = self.get_task(task_id)
        if not task:
            return None

        # Create schedule
        return self.create_schedule(
            date=target_date,
            start_time=start_time,
            end_time=end_time,
            task_id=task_id,
            slot_type='task'
        )

    # ==================== AI Scheduling Suggestion ====================

    def get_ai_schedule_suggestion(self, target_date: date) -> Dict[str, Any]:
        """Get AI-powered schedule suggestion for a day"""
        pending_tasks = self.get_pending_tasks()
        available_slots = self.get_available_slots(target_date)

        if not pending_tasks:
            return {
                'suggestions': [],
                'message': 'No pending tasks to schedule'
            }

        # Simple heuristic: sort by priority and duration
        tasks_to_schedule = []
        for task in pending_tasks[:10]:  # Limit to 10 tasks
            estimated_hours = task.estimated_hours or 1.0
            tasks_to_schedule.append({
                'id': task.id,
                'title': task.title,
                'priority': task.priority.value if hasattr(task.priority, 'value') else task.priority,
                'estimated_hours': estimated_hours
            })

        # Sort by priority
        priority_order = {'high': 0, 'normal': 1, 'low': 2}
        tasks_to_schedule.sort(key=lambda x: priority_order.get(x['priority'], 1))

        # Assign tasks to slots
        suggestions = []
        remaining_slots = available_slots.copy()

        for task in tasks_to_schedule:
            if not remaining_slots:
                break

            # Find best matching slot
            best_slot = None
            for i, slot in enumerate(remaining_slots):
                if task['estimated_hours'] <= 1:
                    best_slot = slot
                    remaining_slots.pop(i)
                    break

            if best_slot:
                suggestions.append({
                    'task_id': task['id'],
                    'task_title': task['title'],
                    'start_time': best_slot['start_time'],
                    'end_time': best_slot['end_time'],
                    'priority': task['priority']
                })

        return {
            'date': target_date.isoformat(),
            'suggestions': suggestions,
            'message': f"Scheduled {len(suggestions)} tasks"
        }

    # ==================== Dashboard ====================

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary"""
        return self.db.get_dashboard_summary()


# Singleton instance
_manager_instance: Optional[ScheduleManager] = None


def get_schedule_manager() -> ScheduleManager:
    """Get schedule manager singleton"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ScheduleManager()
    return _manager_instance
