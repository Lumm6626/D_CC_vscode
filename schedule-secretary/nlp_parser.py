"""
Simple Natural Language Parser for Schedule Secretary
Rule-based parsing without AI API - completely free
"""

import re
from datetime import datetime, date, timedelta, time
from typing import Optional, Dict, Any, List, Tuple


class NLPParser:
    """Simple rule-based NLP parser for schedule commands"""

    # Time patterns
    TIME_PATTERNS = [
        (r'今天', lambda: date.today()),
        (r'明天', lambda: date.today() + timedelta(days=1)),
        (r'后天', lambda: date.today() + timedelta(days=2)),
        (r'大后天', lambda: date.today() + timedelta(days=3)),
    ]

    # Day of week patterns
    WEEKDAY_MAP = {
        '周一': 0, '星期一': 0,
        '周二': 1, '星期二': 1,
        '周三': 2, '星期三': 2,
        '周四': 3, '星期四': 3,
        '周五': 4, '星期五': 4,
        '周六': 5, '星期六': 5,
        '周日': 6, '星期天': 6,
        '星期日': 6,
    }

    # Time of day patterns
    TIME_OF_DAY = {
        '早上': (8, 0),
        '上午': (9, 0),
        '中午': (12, 0),
        '下午': (14, 0),
        '傍晚': (17, 0),
        '晚上': (19, 0),
        '凌晨': (3, 0),
    }

    # Action patterns
    ACTION_PATTERNS = {
        '添加': 'add_task',
        '新增': 'add_task',
        '创建': 'add_task',
        '安排': 'add_schedule',
        '约': 'add_schedule',
        '开会': 'add_schedule',
        '提交': 'add_schedule',
        '面试': 'add_schedule',
        '拜访': 'add_schedule',
        '讨论': 'add_schedule',
        '审核': 'add_schedule',
        '发送': 'add_schedule',
        '回复': 'add_schedule',
        '删除': 'delete',
        '移除': 'delete',
        '取消': 'delete',
        '改到': 'reschedule',
        '修改': 'update',
        '完成': 'complete',
        '标记完成': 'complete',
        '查看': 'view',
        '看看': 'view',
        '有什么': 'view',
    }

    # Task type keywords
    TASK_KEYWORDS = [
        '会议', '开会', 'meeting',
        '报告', '方案', '文档',
        '提交', '发送', '回复',
        '审核', '审批', '检查',
        '面试', '沟通', '讨论',
        '拜访', '拜访客户',
        '写', '做', '完成',
    ]

    def __init__(self):
        self.last_context = {}  # Store context for follow-up commands

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language text into structured command

        Returns:
            {
                'action': 'add_task' | 'add_schedule' | 'view' | etc,
                'title': '任务标题',
                'date': datetime.date,
                'time': datetime.time,
                'duration': int (minutes),
                'confidence': float (0-1),
                'original': 'original text',
                'error': 'error message if failed'
            }
        """
        text = text.strip()
        result = {
            'action': None,
            'title': '',
            'date': None,
            'time': None,
            'duration': 60,
            'confidence': 0.0,
            'original': text,
            'error': None
        }

        # Detect action
        action = self._detect_action(text)
        if not action:
            result['error'] = '无法理解意图'
            return result

        result['action'] = action

        # Parse date and time
        parsed_date, date_confidence = self._parse_date(text)
        parsed_time, time_confidence = self._parse_time(text)

        result['date'] = parsed_date
        result['time'] = parsed_time

        # Extract title/task description
        result['title'] = self._extract_title(text, action)

        # Calculate confidence based on what we successfully parsed
        confidence = 0.3  # Base confidence for detecting action
        if parsed_date:
            confidence += 0.3
        if parsed_time:
            confidence += 0.3
        if result['title']:
            confidence += 0.1

        result['confidence'] = min(confidence, 1.0)

        return result

    def _detect_action(self, text: str) -> Optional[str]:
        """Detect the action intent from text"""
        for keyword, action in self.ACTION_PATTERNS.items():
            if keyword in text:
                return action
        return None

    def _parse_date(self, text: str) -> Tuple[Optional[date], float]:
        """Parse date from text, returns (date, confidence)"""
        today = date.today()

        # Check relative dates first
        for pattern, date_func in self.TIME_PATTERNS:
            if pattern in text:
                return date_func(), 0.9

        # Check weekday references
        for name, weekday in self.WEEKDAY_MAP.items():
            if name in text:
                days_ahead = weekday - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead), 0.9

        # Check for "本周" "下周" patterns
        if '本周' in text:
            # Find the day name
            for name, weekday in self.WEEKDAY_MAP.items():
                if name in text:
                    days_ahead = weekday - today.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    return today + timedelta(days=days_ahead), 0.8
            return today, 0.5

        if '下周' in text:
            for name, weekday in self.WEEKDAY_MAP.items():
                if name in text:
                    days_ahead = weekday - today.weekday() + 7
                    return today + timedelta(days=days_ahead), 0.8

        # Check for specific date "3月15日" or "3-15"
        match = re.search(r'(\d{1,2})[月\-](\d{1,2})[日]?', text)
        if match:
            month, day = int(match.group(1)), int(match.group(2))
            try:
                year = today.year
                if month < today.month:
                    year += 1
                parsed_date = date(year, month, day)
                return parsed_date, 0.9
            except ValueError:
                pass

        # Default to today for schedule actions, None for others
        return today, 0.3

    def _parse_time(self, text: str) -> Tuple[Optional[time], float]:
        """Parse time from text, returns (time, confidence)"""
        # Pattern: "3点", "下午3点", "15:30", "下午3点半"
        match = re.search(r'下午(\d{1,2})点?半?', text)
        if match:
            hour = int(match.group(1))
            has_half = '半' in text
            return time(12 + hour, 30 if has_half else 0), 0.9

        match = re.search(r'上午(\d{1,2})点?半?', text)
        if match:
            hour = int(match.group(1))
            has_half = '半' in text
            return time(hour, 30 if has_half else 0), 0.9

        match = re.search(r'早上(\d{1,2})点?半?', text)
        if match:
            hour = int(match.group(1))
            has_half = '半' in text
            return time(hour, 30 if has_half else 0), 0.9

        match = re.search(r'晚上(\d{1,2})点?半?', text)
        if match:
            hour = int(match.group(1))
            has_half = '半' in text
            return time(hour, 30 if has_half else 0), 0.9

        match = re.search(r'(\d{1,2}):(\d{2})', text)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
            return time(hour, minute), 0.9

        match = re.search(r'(\d{1,2})点', text)
        if match:
            hour = int(match.group(1))
            if 0 <= hour <= 23:
                return time(hour, 0), 0.8

        # Check time of day keywords
        for tod_name, (hour, minute) in self.TIME_OF_DAY.items():
            if tod_name in text:
                return time(hour, minute), 0.7

        return None, 0.0

    def _extract_title(self, text: str, action: str) -> str:
        """Extract the task/title from text"""
        title = text

        # Remove time expressions
        patterns_to_remove = [
            r'今天\s*',
            r'明天\s*',
            r'后天\s*',
            r'大后天\s*',
            r'今天(早上|上午|中午|下午|晚上|凌晨)?',
            r'明天(早上|上午|中午|下午|晚上|凌晨)?',
            r'周[一二三四五六日](?:星期[一二三四五六日])?\s*',
            r'(?:早上|上午|中午|下午|晚上|凌晨)\d{1,2}点?(?:半)?\s*',
            r'\d{1,2}:\d{2}\s*',
            r'\d{1,2}点\s*',
            r'帮我\s*',
            r'请\s*',
            r'安排\s*',
            r'添加\s*',
            r'新增\s*',
            r'创建\s*',
            r'(?:帮我)?安排\s*',
            r'删除(?:我的)?\s*',
            r'取消\s*',
            r'改到\s*',
            r'修改\s*',
            r'完成\s*',
            r'标记完成\s*',
        ]

        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title)

        # Clean up
        title = title.strip()
        title = re.sub(r'\s+', ' ', title)
        # Remove leading "的" for delete actions
        if action == 'delete':
            title = re.sub(r'^的+', '', title)

        return title if title else ''

    def format_response(self, result: Dict[str, Any]) -> str:
        """Format the parsing result into a readable response"""
        if result['error']:
            return f"抱歉，没理解你的意思。请换个说法，比如：「明天下午3点开会」"

        action = result['action']
        title = result['title'] or '新任务'

        # Format date
        date_str = ''
        if result['date']:
            d = result['date']
            today = date.today()
            if d == today:
                date_str = '今天'
            elif d == today + timedelta(days=1):
                date_str = '明天'
            elif d == today + timedelta(days=2):
                date_str = '后天'
            else:
                date_str = d.strftime('%m月%d日')

        # Format time
        time_str = ''
        if result['time']:
            time_str = result['time'].strftime('%H:%M')

        # Generate response based on action
        if action == 'add_task':
            return f"好的，已添加任务「{title}」{'(' + date_str + ')' if date_str else ''}"
        elif action == 'add_schedule':
            when = f"{date_str} {time_str}".strip()
            return f"好的，已安排「{title}」{'于' + when if when else ''}"
        elif action == 'view':
            return "好的，我来查一下..."
        elif action == 'complete':
            return f"好的，标记「{title}」为完成"
        elif action == 'delete':
            return f"好的，删除「{title}」"
        else:
            return f"好的，{action}「{title}」"


# Singleton instance
_nlp_parser = None


def get_nlp_parser() -> NLPParser:
    """Get NLP parser singleton"""
    global _nlp_parser
    if _nlp_parser is None:
        _nlp_parser = NLPParser()
    return _nlp_parser
