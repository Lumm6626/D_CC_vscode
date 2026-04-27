"""
Email Task Extractor
Reuses email parsing logic from daily-report
Extracts tasks from 163 emails
"""
import os
import sys
import re
import ssl
import poplib
from datetime import datetime, timedelta
from email.parser import Parser
from email.header import decode_header
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from secretary_team.daily_report.server import DailyReport
except ImportError:
    # If daily_report is not available, implement basic email reading
    DailyReport = None


def get_pending_reply_emails(max_count: int = 20) -> List[Dict]:
    """
    Get emails that need reply from 163 mailbox.
    Filters out auto-replies, subscriptions, and bulk emails.

    Returns:
        List of email dictionaries with keys:
        - sender_name: Name of sender (extracted from From field)
        - subject: Email subject
        - received_time: Time received (datetime object)
        - time_str: Human readable time string (今天/昨天/HH:MM)
        - needs_reply: bool indicating if reply is needed
        - is_important: bool indicating high priority
        - email_link: URL link to open email in browser
    """
    try:
        config = _load_email_config()
        if not config:
            return []

        emails = []

        # Connect to 163 mailbox
        context = ssl.create_default_context()
        mailbox = poplib.POP3_SSL('pop.163.com', 995, context=context)
        mailbox.user(config['email'])
        mailbox.pass_(config['password'])

        num_messages = len(mailbox.list()[1])
        print(f"Total emails: {num_messages}")

        # Get last N emails
        start = max(1, num_messages - max_count + 1)
        for i in range(num_messages, start - 1, -1):
            try:
                msg_lines = mailbox.retr(i)[1]
                msg_content = b'\r\n'.join(msg_lines).decode('utf-8', errors='ignore')
                msg = Parser().parsestr(msg_content)

                subject = _decode_subject(msg.get('Subject', ''))
                from_addr = msg.get('From', '')
                date_str = msg.get('Date', '')

                # Parse received time
                received_time = _parse_email_date(date_str)
                time_str = _format_time_string(received_time)

                # Extract sender name and email
                sender_name, sender_email = _parse_sender(from_addr)

                # Check if email needs reply
                needs_reply, is_important = _analyze_email_needs_reply(subject, msg)

                # Skip auto-replies and subscriptions
                if _is_auto_or_bulk(msg, subject):
                    continue

                if needs_reply:
                    emails.append({
                        'sender_name': sender_name,
                        'subject': subject,
                        'received_time': received_time,
                        'time_str': time_str,
                        'needs_reply': needs_reply,
                        'is_important': is_important,
                        'email_link': f"https://mail.163.com/#from={sender_email}&subject={subject}"
                    })

            except Exception as e:
                continue

        mailbox.quit()
        return emails

    except Exception as e:
        print(f"Error getting pending reply emails: {e}")
        return []


def format_pending_emails_message(emails: List[Dict]) -> str:
    """Format pending emails list as Feishu message"""
    if not emails:
        return "📧 暂无待回复邮件"

    message = f"📧 待回复邮件 ({len(emails)}封)\n\n"

    for i, email in enumerate(emails[:10], 1):
        priority_icon = "🔴" if email.get('is_important') else "📬"
        message += f"{i}. [{email['sender_name']}] {email['subject']} - {email['time_str']}\n"

    return message


def get_email_tasks(max_count: int = 50) -> List[Dict]:
    """
    Get tasks from 163 email inbox

    Returns:
        List of task dictionaries with keys:
        - title: Task title
        - description: Task description
        - priority: high/normal/low
        - source: email
        - email_subject: Original email subject
        - from_email: Sender email
    """
    if DailyReport is None:
        # Fallback implementation without daily-report
        return _get_tasks_from_email_basic()

    try:
        # Use the DailyReport class from daily-report
        report = DailyReport(config_path="config/email_config.json")
        report.get_emails(max_count=max_count)

        tasks = []
        for todo in report.todos:
            tasks.append({
                'title': todo.get('subject', 'Untitled')[:100],
                'description': todo.get('body', '')[:500],
                'priority': todo.get('priority', 'normal'),
                'source': 'email',
                'email_subject': todo.get('subject', ''),
                'from_email': todo.get('from_email', '')
            })

        return tasks

    except Exception as e:
        print(f"Error extracting email tasks: {e}")
        return []


def _get_tasks_from_email_basic() -> List[Dict]:
    """Basic email task extraction without daily-report dependency"""
    try:
        config = _load_email_config()
        if not config:
            return []

        tasks = []

        # Connect to 163 mailbox
        context = ssl.create_default_context()
        mailbox = poplib.POP3_SSL('pop.163.com', 995, context=context)
        mailbox.user(config['email'])
        mailbox.pass_(config['password'])

        num_messages = len(mailbox.list()[1])
        print(f"Total emails: {num_messages}")

        # Get last N emails
        start = max(1, num_messages - 50 + 1)
        for i in range(num_messages, start - 1, -1):
            try:
                msg_lines = mailbox.retr(i)[1]
                msg_content = b'\r\n'.join(msg_lines).decode('utf-8', errors='ignore')
                msg = Parser().parsestr(msg_content)

                subject = _decode_subject(msg.get('Subject', ''))
                from_addr = msg.get('From', '')
                body = _get_email_body(msg)

                # Extract tasks from email
                email_tasks = _extract_tasks_from_text(subject, body)
                for task in email_tasks:
                    task['from_email'] = _extract_email_addr(from_addr)
                    task['email_subject'] = subject
                    tasks.append(task)

            except Exception as e:
                continue

        mailbox.quit()
        return tasks

    except Exception as e:
        print(f"Error in basic email extraction: {e}")
        return []


def _load_email_config() -> Optional[Dict]:
    """Load email configuration"""
    config_path = os.path.join(
        os.path.dirname(__file__),
        '..', 'secretary-team', 'config', 'email_config.json'
    )

    if os.path.exists(config_path):
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def _decode_subject(subject: str) -> str:
    """Decode email subject"""
    if not subject:
        return ""

    decoded_parts = decode_header(subject)
    result = ""
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            charset = charset or 'utf-8'
            try:
                result += part.decode(charset, errors='ignore')
            except:
                result += part.decode('utf-8', errors='ignore')
        else:
            result += part
    return result


def _extract_email_addr(from_addr: str) -> str:
    """Extract email address from From field"""
    match = re.search(r'<([^>]+)>', from_addr)
    if match:
        return match.group(1)
    match = re.search(r'[\w\.-]+@[\w\.-]+', from_addr)
    if match:
        return match.group(0)
    return from_addr


def _get_email_body(msg) -> str:
    """Get email body text"""
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body = payload.decode('utf-8', errors='ignore')
                else:
                    body = str(payload)
                break
        if not body:
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body = payload.decode('utf-8', errors='ignore')
                    else:
                        body = str(payload)
                    break
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            body = payload.decode('utf-8', errors='ignore')
        else:
            body = str(payload)

    # Clean HTML
    body = re.sub(r'<[^>]+>', '', body)
    body = body.replace('&nbsp;', ' ').replace('&amp;', '&')
    body = body.replace('\r\n', '\n').replace('\n', ' ').strip()
    return body


def _extract_tasks_from_text(subject: str, body: str) -> List[Dict]:
    """Extract tasks from email subject and body"""
    tasks = []
    content = f"{subject} {body}".lower()

    # Keywords that indicate action items
    action_keywords = [
        '请', '需要', '希望', '期待', '能否', '帮忙',
        '合作', '洽谈', '沟通', '回复', '确认',
        '报价', '方案', '合同', '报价单', 'todo', '待办', '任务'
    ]

    # High priority keywords
    high_priority_keywords = [
        '紧急', '重要', '急', 'asap', '商务合作', '投放',
        '面试', 'offer', '录用'
    ]

    # Check if content has action items
    action_count = sum(1 for kw in action_keywords if kw in content)

    if action_count >= 1:
        # Extract a title from subject
        title = subject[:100] if subject else "Email Task"

        # Determine priority
        priority = 'normal'
        if any(kw in content for kw in high_priority_keywords):
            priority = 'high'

        # Special handling for collaboration opportunities
        collab_keywords = ['抖音', '小红书', 'b站', '快手', '达人', 'koc', 'kol', '种草', '带货']
        if any(kw in content for kw in collab_keywords):
            priority = 'high'

        tasks.append({
            'title': title,
            'description': body[:500] if body else '',
            'priority': priority,
            'source': 'email'
        })

    return tasks


def _parse_sender(from_addr: str) -> tuple:
    """Parse sender name and email from From field"""
    # Format: "Name <email@example.com>" or just "email@example.com"
    match = re.search(r'([^<]+)\s*<([^>]+)>', from_addr)
    if match:
        name = match.group(1).strip().strip('"').strip()
        email = match.group(2).strip()
        return (name, email) if name else (email.split('@')[0], email)

    match = re.search(r'[\w\.-]+@[\w\.-]+', from_addr)
    if match:
        email = match.group(0)
        return (email.split('@')[0], email)
    return (from_addr, from_addr)


def _parse_email_date(date_str: str) -> datetime:
    """Parse email Date header to datetime"""
    if not date_str:
        return datetime.now()

    try:
        # Try common email date formats
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except:
        pass

    # Fallback: try basic parsing
    try:
        return datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
    except:
        pass

    return datetime.now()


def _format_time_string(dt: datetime) -> str:
    """Format datetime as human readable string"""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    if dt >= today_start:
        return f"今天 {dt.strftime('%H:%M')}"
    elif dt >= yesterday_start:
        return f"昨天 {dt.strftime('%H:%M')}"
    else:
        return dt.strftime('%m月%d日 %H:%M')


def _analyze_email_needs_reply(subject: str, msg) -> tuple:
    """Analyze if email needs reply and if it's important"""
    subject_lower = subject.lower()

    # Auto-reply keywords (should not need reply)
    auto_keywords = ['自动回复', 'auto reply', 'out of office', 'oof',
                     '已自动回复', '收到', '谢谢', 'thank you', '收到谢谢']

    # Important keywords
    important_keywords = ['紧急', '重要', '急', 'asap', '商务合作', '面试',
                        'offer', '录用', '合同', '报价', '方案', '请', '需要']

    # Action keywords (indicates needs reply)
    action_keywords = ['请', '需要', '希望', '期待', '能否', '帮忙',
                      '合作', '洽谈', '沟通', '回复', '确认', '反馈']

    subject_has_auto = any(kw in subject_lower for kw in auto_keywords)
    subject_has_important = any(kw in subject_lower for kw in important_keywords)
    subject_has_action = any(kw in subject_lower for kw in action_keywords)

    # Check for collaboration keywords
    collab_keywords = ['抖音', '小红书', 'b站', '快手', '达人', 'koc', 'kol', '种草', '带货']
    if any(kw in subject_lower for kw in collab_keywords):
        subject_has_important = True

    needs_reply = subject_has_action and not subject_has_auto
    is_important = subject_has_important

    return needs_reply, is_important


def _is_auto_or_bulk(msg, subject: str) -> bool:
    """Check if email is auto-reply or bulk email"""
    subject_lower = subject.lower()

    # Check headers
    headers = dict(msg.items())

    # Auto-reply indicators
    auto_headers = {
        'auto-submitted': 'auto-replied',
        'x-autoreply': 'yes',
        'x-mailer': 'auto',
    }

    for header, value in auto_headers.items():
        if header in headers and headers[header].lower() == value:
            return True

    # Check List-ID header (indicates mailing list)
    if 'list-id' in headers or 'list-unsubscribe' in headers:
        return True

    # Check subject for bulk indicators
    bulk_keywords = ['退订', 'unsubscribe', 'newsletter', 'news letter',
                    '订阅', '通知', '公告', 'newsletter', 'marketing']

    if any(kw in subject_lower for kw in bulk_keywords):
        return True

    return False


def import_tasks_to_schedule() -> List[Dict]:
    """
    Import email tasks directly to schedule manager

    Returns:
        List of created Task objects
    """
    from schedule_manager import get_schedule_manager

    email_tasks = get_email_tasks()
    manager = get_schedule_manager()
    created_tasks = []

    for task_data in email_tasks[:10]:  # Limit to 10 tasks
        task = manager.create_task(
            title=task_data['title'],
            description=task_data.get('description', ''),
            source='email',
            priority=task_data.get('priority', 'normal')
        )
        created_tasks.append(task)

    return created_tasks


if __name__ == "__main__":
    # Test
    tasks = get_email_tasks()
    print(f"Found {len(tasks)} tasks from email")
    for task in tasks[:5]:
        print(f"  - {task['title']} ({task['priority']})")
