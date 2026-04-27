"""
Feishu Bot for Schedule Secretary
Extended from review-assistant/feishu/bot.py
Handles reminders, notifications, and simple interactions
"""
import os
import re
import json
import requests
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
load_dotenv()

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")


def get_tenant_access_token() -> str:
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    if result.get("code") == 0:
        return result.get("tenant_access_token")
    else:
        raise Exception(f"获取tenant_access_token失败: {result}")


def send_text_message(message: str, receive_id: str = None) -> dict:
    """
    发送文本消息

    Args:
        message: 消息内容
        receive_id: 用户ID（可选，如果不提供则发送到Webhook）

    Returns:
        API响应结果
    """
    if receive_id:
        return send_p2p_message(receive_id, message)
    else:
        return send_webhook_message(message)


def send_webhook_message(message: str) -> dict:
    """通过Webhook发送消息"""
    payload = {
        "msg_type": "text",
        "content": {
            "text": message
        }
    }
    response = requests.post(FEISHU_WEBHOOK_URL, json=payload)
    return response.json()


def send_p2p_message(receive_id: str, message: str) -> dict:
    """发送P2P私聊消息"""
    token = get_tenant_access_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    open_id = receive_id if receive_id.startswith("ou_") else get_user_open_id(receive_id)
    params = {
        "receive_id": open_id,
        "receive_id_type": "open_id"
    }
    data = {
        "receive_id": open_id,
        "msg_type": "text",
        "content": '{"text":"' + message + '"}'
    }

    response = requests.post(url, headers=headers, json=data, params=params)
    return response.json()


def send_task_card(tasks: List[Dict], receive_id: str = None) -> dict:
    """发送任务卡片消息"""
    # Build task list text
    task_text = ""
    for i, task in enumerate(tasks[:10], 1):
        priority_emoji = "🔴" if task.get('priority') == 'high' else "🟡" if task.get('priority') == 'normal' else "🟢"
        status_emoji = "✅" if task.get('status') == 'completed' else "📋"
        task_text += f"{status_emoji} {priority_emoji} {task.get('title', 'Untitled')}\n"

    if not task_text:
        task_text = "暂无任务"

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📋 任务列表"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": task_text
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "回复「完成 <ID>」标记任务完成"
                        }
                    ]
                }
            ]
        }
    }

    if receive_id:
        token = get_tenant_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        open_id = receive_id if receive_id.startswith("ou_") else get_user_open_id(receive_id)
        params = {"receive_id": open_id}
        data = {
            "receive_id": open_id,
            "msg_type": "interactive",
            "content": json.dumps({"card": card["card"]})
        }
        response = requests.post(url, headers=headers, json=data, params=params)
        return response.json()
    else:
        response = requests.post(FEISHU_WEBHOOK_URL, json=card)
        return response.json()


def send_schedule_card(schedules: List[Dict], receive_id: str = None) -> dict:
    """发送日程卡片消息"""
    schedule_text = ""
    for s in schedules[:10]:
        time_str = ""
        if s.get('start_time'):
            time_str = s.get('start_time', '')[:5]
            if s.get('end_time'):
                time_str += f" - {s.get('end_time', '')[:5]}"

        status_emoji = "✅" if s.get('status') == 'done' else "📅"
        title = s.get('task_title') or s.get('slot_type', '日程')
        schedule_text += f"{status_emoji} {time_str} {title}\n"

    if not schedule_text:
        schedule_text = "今日暂无日程"

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📅 {date.today().strftime('%Y年%m月%d日')} 日程"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": schedule_text
                }
            ]
        }
    }

    if receive_id:
        token = get_tenant_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        open_id = receive_id if receive_id.startswith("ou_") else get_user_open_id(receive_id)
        params = {"receive_id": open_id}
        data = {
            "receive_id": open_id,
            "msg_type": "interactive",
            "content": json.dumps({"card": card["card"]})
        }
        response = requests.post(url, headers=headers, json=data, params=params)
        return response.json()
    else:
        response = requests.post(FEISHU_WEBHOOK_URL, json=card)
        return response.json()


def get_user_open_id(user_id: str) -> str:
    """根据用户ID获取open_id"""
    token = get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/contact/v3/users/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    result = response.json()

    if result.get("code") == 0:
        return result.get("data", {}).get("user", {}).get("open_id", user_id)
    return user_id


def parse_command(text: str) -> Dict[str, Any]:
    """Parse user command from bot message"""
    text = text.strip()

    # Quick add task: "添加任务 <标题>"
    match = re.match(r'^添加任务\s*(.+)$', text)
    if match:
        return {'command': 'add_task', 'title': match.group(1)}

    # Complete task: "完成 <ID>"
    match = re.match(r'^完成\s*(\d+)$', text)
    if match:
        return {'command': 'complete_task', 'task_id': int(match.group(1))}

    # View tasks: "查看任务"
    if '查看任务' in text:
        return {'command': 'view_tasks'}

    # View schedule: "查看日程"
    if '查看日程' in text:
        return {'command': 'view_schedule'}

    # AI plan: "帮我规划今天"
    if '帮我规划今天' in text or '规划今天' in text:
        return {'command': 'ai_plan'}

    # Import from email: "导入邮件任务"
    if '导入邮件任务' in text:
        return {'command': 'import_email'}

    # Start review: "开始复盘" or "复盘"
    if '开始复盘' in text or text == '复盘':
        return {'command': 'start_review'}

    # Review response (any text when in review mode)
    # Check if there's an active review session
    try:
        from review_service import get_review_service
        review_service = get_review_service()
        from datetime import date
        today = date.today()
        review = review_service.get_review_by_date(today)
        if review and not review.get('completed'):
            # User is in review mode, route to review handler
            return {'command': 'review_response', 'text': text}
    except Exception as e:
        print(f"Review check error: {e}")

    # Help
    if '帮助' in text or 'help' in text.lower():
        return {'command': 'help'}

    # Try natural language parsing
    try:
        from nlp_parser import get_nlp_parser
        parser = get_nlp_parser()
        parsed = parser.parse(text)
        if parsed['confidence'] > 0.3:
            return {'command': 'nlp', 'parsed': parsed}
    except Exception as e:
        print(f"NLP parse error: {e}")

    return {'command': 'unknown', 'text': text}


def handle_command(command: Dict[str, Any]) -> str:
    """Handle parsed command and return response message"""
    from schedule_manager import get_schedule_manager

    manager = get_schedule_manager()

    cmd = command.get('command')

    if cmd == 'add_task':
        title = command.get('title', '')
        if not title:
            return "请提供任务标题，例如：「添加任务 完成报告」"
        task = manager.create_task(title=title, source='manual')
        return f"✅ 任务已添加：{task.title}\n优先级：{task.priority.value if hasattr(task.priority, 'value') else task.priority}\n状态：pending"

    elif cmd == 'complete_task':
        task_id = command.get('task_id')
        if manager.complete_task(task_id):
            return f"✅ 任务 {task_id} 已标记完成"
        return f"❌ 任务 {task_id} 不存在"

    elif cmd == 'view_tasks':
        tasks = manager.get_tasks(status='pending')
        if not tasks:
            return "📋 当前没有待办任务"
        return format_task_list(tasks)

    elif cmd == 'view_schedule':
        schedules = manager.get_today_schedules()
        if not schedules:
            return "📅 今天暂无日程安排"
        return format_schedule_list(schedules)

    elif cmd == 'ai_plan':
        suggestion = manager.get_ai_schedule_suggestion(date.today())
        if suggestion.get('suggestions'):
            response = "🤖 AI 今日规划建议：\n\n"
            for s in suggestion['suggestions']:
                response += f"⏰ {s['start_time'][:5]} - {s['end_time'][:5]}\n"
                response += f"   {s['task_title']}\n\n"
            response += f"已安排 {len(suggestion['suggestions'])} 项任务"
            return response
        return "📭 暂无任务需要规划"

    elif cmd == 'import_email':
        from email_task_extractor import get_email_tasks
        tasks = get_email_tasks()
        if tasks:
            added = []
            for t in tasks[:5]:
                task = manager.create_task(
                    title=t.get('title', 'From Email'),
                    description=t.get('description', ''),
                    source='email',
                    priority=t.get('priority', 'normal')
                )
                added.append(task.title)
            return f"📧 已从邮件导入 {len(added)} 项任务：\n" + "\n".join(f"• {t}" for t in added)
        return "📭 未从邮件中找到待办事项"

    elif cmd == 'start_review':
        from review_service import get_review_service
        review_service = get_review_service()
        result = review_service.start_review()
        return result.get('message', '抱歉，复盘服务暂时不可用')

    elif cmd == 'review_response':
        from review_service import get_review_service
        review_service = get_review_service()
        user_text = command.get('text', '')
        result = review_service.process_review_response(user_text)
        if result.get('is_complete'):
            return (
                f"{result.get('message', '')}\n\n"
                f"📋 复盘已保存!"
            )
        return result.get('message', '收到，请继续...')

    elif cmd == 'nlp':
        parsed = command.get('parsed', {})
        action = parsed.get('action', '')
        title = parsed.get('title', '新任务')
        target_date = parsed.get('date')
        target_time = parsed.get('time')
        nlp_parser = get_nlp_parser()

        if action in ('add_task', 'add_schedule'):
            if not title:
                return "没听清任务内容，请再说一次？"

            task = manager.create_task(
                title=title,
                source='manual',
                priority='normal',
                due_date=target_date
            )

            if action == 'add_schedule' and target_date and target_time:
                # Calculate end time (default 1 hour)
                from datetime import timedelta
                start_dt = datetime.combine(target_date, target_time)
                end_dt = start_dt + timedelta(hours=1)
                manager.create_schedule(
                    date=target_date,
                    start_time=target_time,
                    end_time=end_dt.time(),
                    task_id=task.id,
                    slot_type='task'
                )

                when = target_date.strftime('%m月%d日') if target_date else '今天'
                time_str = target_time.strftime('%H:%M') if target_time else ''
                return f"✅ 已安排「{title}」\n📅 {when} {time_str}"

            return f"✅ 已添加任务「{title}」"

        elif action == 'view':
            return handle_command({'command': 'view_tasks'})

        elif action == 'complete':
            # Find and complete matching task
            tasks = manager.get_tasks(status='pending')
            for t in tasks:
                if title.lower() in t.title.lower():
                    manager.complete_task(t.id)
                    return f"✅ 「{t.title}」已标记完成"
            return f"没找到任务「{title}」"

        elif action == 'delete':
            tasks = manager.get_tasks()
            for t in tasks:
                if title.lower() in t.title.lower():
                    manager.delete_task(t.id)
                    return f"🗑️ 「{t.title}」已删除"
            return f"没找到任务「{title}」"

        return nlp_parser.format_response(parsed)

    elif cmd == 'help':
        return """📚 可用命令：

【固定命令】
• 添加任务 <标题> - 快速添加任务
• 查看任务 - 查看待办列表
• 查看日程 - 查看今日日程
• 完成 <ID> - 标记任务完成
• 导入邮件任务 - 从邮件导入待办

【自然语言】
直接说就行，比如：
• 明天下午3点开会
• 周五提交报告
• 帮我安排后天上午9点面试
• 删除明天的会议

• 帮助 - 显示此帮助"""

    else:
        return "🤔 没听懂，请换个说法，或者输入「帮助」查看命令"


def get_nlp_parser():
    """Import and return NLP parser"""
    import nlp_parser
    return nlp_parser.get_nlp_parser()


def format_task_list(tasks: List) -> str:
    """Format task list for display"""
    result = "📋 待办任务：\n\n"
    for i, task in enumerate(tasks[:10], 1):
        priority = task.priority.value if hasattr(task.priority, 'value') else task.priority
        emoji = "🔴" if priority == 'high' else "🟡" if priority == 'normal' else "🟢"
        result += f"{i}. {emoji} {task.title}\n"
        result += f"   ID: {task.id} | 状态: {task.status.value if hasattr(task.status, 'value') else task.status}\n\n"
    return result


def format_schedule_list(schedules: List) -> str:
    """Format schedule list for display"""
    result = f"📅 今日日程：\n\n"
    today = date.today().strftime('%Y年%m月%d日')

    for s in schedules[:10]:
        time_str = ""
        if s.start_time:
            time_str = s.start_time.strftime('%H:%M') if hasattr(s.start_time, 'strftime') else s.start_time[:5]
            if s.end_time:
                time_str += f" - {s.end_time.strftime('%H:%M') if hasattr(s.end_time, 'strftime') else s.end_time[:5]}"

        status = s.status.value if hasattr(s.status, 'value') else s.status
        emoji = "✅" if status == 'done' else "📅"
        title = s.task_title or (s.slot_type.value if hasattr(s.slot_type, 'value') else s.slot_type)

        result += f"{emoji} {time_str} {title}\n"

    return result


if __name__ == "__main__":
    # Test sending
    result = send_webhook_message("Schedule Secretary Bot 已启动")
    print(f"发送结果: {result}")
