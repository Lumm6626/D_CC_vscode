"""
Data models for Schedule Secretary
"""
from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional, List
from enum import Enum


class TaskSource(str, Enum):
    MANUAL = "manual"
    EMAIL = "email"
    ROUTINE = "routine"


class TaskPriority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class SlotType(str, Enum):
    TASK = "task"
    MEETING = "meeting"
    BREAK = "break"
    ROUTINE = "routine"


class ScheduleStatus(str, Enum):
    SCHEDULED = "scheduled"
    DONE = "done"
    MISSED = "missed"


@dataclass
class Task:
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    source: TaskSource = TaskSource.MANUAL
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'source': self.source.value if isinstance(self.source, TaskSource) else self.source,
            'priority': self.priority.value if isinstance(self.priority, TaskPriority) else self.priority,
            'status': self.status.value if isinstance(self.status, TaskStatus) else self.status,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'estimated_hours': self.estimated_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            source=TaskSource(data.get('source', 'manual')),
            priority=TaskPriority(data.get('priority', 'normal')),
            status=TaskStatus(data.get('status', 'pending')),
            due_date=date.fromisoformat(data['due_date']) if data.get('due_date') else None,
            estimated_hours=data.get('estimated_hours'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )


@dataclass
class Schedule:
    id: Optional[int] = None
    task_id: Optional[int] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    slot_type: SlotType = SlotType.TASK
    status: ScheduleStatus = ScheduleStatus.SCHEDULED
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Joined fields
    task_title: Optional[str] = None
    task_description: Optional[str] = None
    task_priority: Optional[str] = None
    task_status: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'slot_type': self.slot_type.value if isinstance(self.slot_type, SlotType) else self.slot_type,
            'status': self.status.value if isinstance(self.status, ScheduleStatus) else self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'task_title': self.task_title,
            'task_description': self.task_description,
            'task_priority': self.task_priority,
            'task_status': self.task_status
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Schedule':
        return cls(
            id=data.get('id'),
            task_id=data.get('task_id'),
            date=date.fromisoformat(data['date']) if data.get('date') else None,
            start_time=time.fromisoformat(data['start_time']) if data.get('start_time') else None,
            end_time=time.fromisoformat(data['end_time']) if data.get('end_time') else None,
            slot_type=SlotType(data.get('slot_type', 'task')),
            status=ScheduleStatus(data.get('status', 'scheduled')),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            task_title=data.get('task_title'),
            task_description=data.get('task_description'),
            task_priority=data.get('task_priority'),
            task_status=data.get('task_status')
        )


@dataclass
class DailyRoutine:
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    time_of_day: Optional[time] = None
    days_of_week: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    duration_minutes: int = 60
    is_active: bool = True
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'time_of_day': self.time_of_day.isoformat() if self.time_of_day else None,
            'days_of_week': self.days_of_week,
            'duration_minutes': self.duration_minutes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DailyRoutine':
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            time_of_day=time.fromisoformat(data['time_of_day']) if data.get('time_of_day') else None,
            days_of_week=data.get('days_of_week', [1, 2, 3, 4, 5]),
            duration_minutes=data.get('duration_minutes', 60),
            is_active=data.get('is_active', True),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        )
