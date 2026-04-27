#!/usr/bin/env python3
"""
日报助理 (daily-report)
功能：查看163邮箱邮件，智能分析分类，生成待办事项并发送HTML日报
"""

import json
import os
import sys
import argparse
import ssl
import poplib
import imaplib
import smtplib
import re
import base64
from datetime import datetime
from email.parser import Parser
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import webbrowser


class DailyReport:
    def __init__(self, config_path="config/email_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.emails = []
        self.todos = []
        self.server = None
        self.server_thread = None
        self.categories = {
            "自媒体合作": [],
            "招聘求职": [],
            "工作邮件": [],
            "社交通知": [],
            "推广营销": [],
            "其他": []
        }

    def _load_config(self):
        """加载配置文件"""
        config_file = os.path.join(os.path.dirname(__file__), "..", self.config_path)
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _decode_subject(self, subject):
        """解码邮件主题（MIME编码的中文主题）"""
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

    def _extract_email_addr(self, from_addr):
        """提取邮件地址"""
        match = re.search(r'<([^>]+)>', from_addr)
        if match:
            return match.group(1)
        # 可能是纯邮箱地址
        match = re.search(r'[\w\.-]+@[\w\.-]+', from_addr)
        if match:
            return match.group(0)
        return from_addr

    def connect_mailbox(self):
        """连接邮箱"""
        try:
            context = ssl.create_default_context()
            mailbox = poplib.POP3_SSL('pop.163.com', 995, context=context)
            mailbox.user(self.config["email"])
            mailbox.pass_(self.config["password"])
            return mailbox
        except Exception as e:
            print(f"连接邮箱失败: {str(e)}")
            return None

    def connect_imap(self):
        """连接IMAP邮箱（用于标记已读）"""
        try:
            mailbox = imaplib.IMAP4_SSL('imap.163.com', 993)
            mailbox.login(self.config["email"], self.config["password"])
            return mailbox
        except Exception as e:
            print(f"IMAP连接失败: {str(e)}")
            return None

    def mark_as_read(self, email_id):
        """标记指定邮件为已读"""
        mailbox = self.connect_imap()
        if not mailbox:
            return False, "IMAP连接失败"

        try:
            mailbox.select('INBOX')
            # 使用邮件ID来标记
            result, msg_ids = mailbox.fetch(email_id, '(UID)')
            if result == 'OK' and msg_ids[0]:
                # 提取UID
                uid_match = re.search(rb'UID (\d+)', msg_ids[0])
                if uid_match:
                    uid = uid_match.group(1)
                    # STORE命令标记为已读（设置 \Seen 标志）
                    mailbox.uid('STORE', uid, '+FLAGS', '\\Seen')
                    mailbox.logout()
                    return True, "已标记为已读"
            mailbox.logout()
            return False, "未找到邮件"
        except Exception as e:
            return False, f"标记失败: {str(e)}"

    def mark_multiple_as_read(self, email_ids):
        """批量标记邮件为已读"""
        results = []
        for email_id in email_ids:
            success, msg = self.mark_as_read(email_id)
            results.append({"id": email_id, "success": success, "message": msg})
        return results

    def _get_email_body(self, msg):
        """获取邮件正文"""
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body = payload.decode('utf-8', errors='ignore')
                    else:
                        body = str(payload)
                    break
            if not body:
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/html':
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

        # 清理HTML标签
        body = re.sub(r'<[^>]+>', '', body)
        body = body.replace('&nbsp;', ' ').replace('&amp;', '&')
        body = body.replace('\r\n', '\n').replace('\n', ' ').strip()
        return body

    def _classify_email(self, subject, body, from_addr):
        """分类邮件"""
        content = (subject + ' ' + body).lower()

        # 重点：自媒体平台商务合作
        platform_keywords = [
            '抖音', '小红书', 'bilibili', 'b站', '快手', '视频号',
            'weibo', '微博', 'instagram', 'youtube', 'tiktok',
            '博主', '达人', 'koc', 'kol', '种草', '带货', '引流',
            '商务合作', 'bd', 'branding', '品牌合作', '投放',
            '探店', '素人', '推广合作', '媒介', 'mcn'
        ]

        if any(kw in content for kw in platform_keywords):
            return "自媒体合作"

        # 招聘求职
        job_keywords = [
            'job', '职位', '招聘', '求职', '面试', '简历',
            '猎头', '内推', 'offer', '薪资', '面试邀请',
            'linkedin', 'indeed', '招聘网站', '51job', 'boss直聘',
            'marketing manager', '产品经理', '运营', '市场经理'
        ]

        if any(kw in content for kw in job_keywords):
            return "招聘求职"

        # 工作邮件
        work_keywords = [
            '回复', '请查收', '请确认', '请注意', '紧急',
            '会议', 'meeting', 'deadline', '截止', '方案',
            '报告', '总结', '审批', 'approve'
        ]

        if any(kw in content for kw in work_keywords):
            return "工作邮件"

        # 社交通知
        social_keywords = [
            'linkedin', 'facebook', 'twitter', 'instagram',
            '有人关注了你', '有人赞', '有人评论', '通知',
            'connection', 'message', '私信'
        ]

        if any(kw in content for kw in social_keywords):
            return "社交通知"

        # 推广营销
        marketing_keywords = [
            '优惠', '促销', '折扣', '免费', '限时', '活动',
            'newsletter', '订阅', '更新', '升级', 'vip'
        ]

        if any(kw in content for kw in marketing_keywords):
            return "推广营销"

        return "其他"

    def _is_important(self, subject, body, from_addr):
        """判断是否为重要/需要处理的邮件"""
        content = (subject + ' ' + body).lower()

        # 排除自动发送邮件
        auto_keywords = ['no-reply', 'noreply', 'auto', '系统', '自动', '提醒', 'notification']
        if all(kw not in from_addr.lower() for kw in ['抖音', '小红书', 'bilibili', 'b站', '快手', '视频号', '达人', '商务合作', '投放', '媒介', 'mcn', '种草']):
            if any(kw in from_addr.lower() for kw in auto_keywords):
                return False

        # 需要处理的邮件特征
        action_keywords = [
            '请', '需要', '希望', '期待', '能否', '帮忙',
            '合作', '洽谈', '沟通', '回复', '确认',
            '报价', '方案', '合同', '报价单'
        ]

        important_keywords = [
            '商务合作', '投放', '抖音', '小红书', 'b站', '快手',
            '达人', 'koc', 'kol', '种草', '带货',
            '面试', 'offer', '录用', '入职',
            '紧急', '重要', '急', 'asap'
        ]

        if any(kw in content for kw in important_keywords):
            return True

        if sum(1 for kw in action_keywords if kw in content) >= 2:
            return True

        return False

    def get_emails(self, max_count=100):
        """获取并分析所有邮件"""
        mailbox = self.connect_mailbox()
        if not mailbox:
            return []

        emails = []
        todos = []
        categories = {k: [] for k in self.categories}

        try:
            num_messages = len(mailbox.list()[1])
            print(f"总邮件数量: {num_messages}")

            start = max(1, num_messages - max_count + 1)
            for i in range(num_messages, start - 1, -1):
                try:
                    msg_lines = mailbox.retr(i)[1]
                    msg_content = b'\r\n'.join(msg_lines).decode('utf-8', errors='ignore')
                    msg = Parser().parsestr(msg_content)

                    # 解码主题
                    subject_raw = msg.get('Subject', '(无主题)')
                    subject = self._decode_subject(subject_raw)
                    from_addr = msg.get('From', '')
                    from_email = self._extract_email_addr(from_addr)
                    date = msg.get('Date', '')
                    body = self._get_email_body(msg)

                    # 分类
                    category = self._classify_email(subject, body, from_addr)

                    email_data = {
                        "id": str(i),  # 使用POP3邮件序号作为ID
                        "message_id": msg.get('Message-ID', ''),
                        "from": from_addr,
                        "from_email": from_email,
                        "subject": subject,
                        "subject_raw": subject_raw,
                        "date": date,
                        "body": body[:500],
                        "category": category
                    }

                    categories[category].append(email_data)

                    # 标记重要邮件为待办
                    if self._is_important(subject, body, from_addr):
                        todo = {
                            "id": str(i),
                            "subject": subject,
                            "from": from_addr,
                            "from_email": from_email,
                            "date": date,
                            "category": category,
                            "body": body[:200],
                            "priority": "high" if category == "自媒体合作" else "normal"
                        }
                        todos.append(todo)

                    emails.append(email_data)

                except Exception as e:
                    continue

        except Exception as e:
            print(f"获取邮件失败: {str(e)}")
        finally:
            try:
                mailbox.quit()
            except:
                pass

        self.emails = emails
        self.todos = sorted(todos, key=lambda x: (0 if x['priority'] == 'high' else 1, x['date']), reverse=True)
        self.categories = categories
        print(f"读取了 {len(emails)} 封邮件")
        print(f"待办事项: {len(todos)} 项")
        return emails

    def _generate_html_report(self, tasks=None):
        """生成HTML日报"""
        today = datetime.now().strftime("%Y-%m-%d")

        # 待办事项HTML - 可点击跳转
        todo_rows = ""
        if self.todos:
            for i, todo in enumerate(self.todos[:15], 1):
                priority_color = "#e53935" if todo['priority'] == 'high' else "#757575"
                priority_text = "紧急" if todo['priority'] == 'high' else "普通"
                category_emoji = {
                    "自媒体合作": "自媒体",
                    "招聘求职": "招聘",
                    "工作邮件": "工作",
                    "社交通知": "社交",
                    "推广营销": "推广",
                    "其他": "其他"
                }.get(todo['category'], "其他")

                # 邮件链接
                mailto_link = f"mailto:{todo['from_email']}?subject=Re:{todo['subject']}"
                subject_encoded = todo['subject'][:50]

                todo_rows += f'''
                <li style="padding: 14px; border-bottom: 1px solid #eee; display: flex; align-items: flex-start; gap: 10px;" data-email-id="{todo['id']}">
                    <input type="checkbox" style="margin-top: 3px; width: 18px; height: 18px; flex-shrink: 0;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                            <a href="{mailto_link}" style="font-weight: 600; color: #1976d2; text-decoration: none; font-size: 15px;" target="_blank">{todo['subject'][:70]}</a>
                            <span style="background: {priority_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{priority_text}</span>
                            <span style="background: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{category_emoji}</span>
                        </div>
                        <div style="font-size: 13px; color: #666; margin-bottom: 4px;">
                            <span style="color: #999;">发件人:</span> {todo['from']}
                        </div>
                        <div style="font-size: 12px; color: #888; line-height: 1.4;">{todo['body'][:120]}</div>
                        <div style="margin-top: 8px; display: flex; gap: 10px; align-items: center;">
                            <a href="{mailto_link}" style="color: #43a047; font-size: 12px; text-decoration: none;">[回复邮件]</a>
                            <button onclick="markAsRead('{todo['id']}', this)" style="background: #757575; color: white; border: none; padding: 4px 10px; border-radius: 4px; font-size: 11px; cursor: pointer;">标记已读</button>
                            <span class="read-status" style="font-size: 11px; color: #43a047; display: none;">✓ 已标记</span>
                        </div>
                    </div>
                </li>'''
        else:
            todo_rows = '<li style="padding: 20px; text-align: center; color: #999;">暂无待办事项</li>'

        # 分类邮件HTML - 可点击
        category_html = ""
        for cat, emails in self.categories.items():
            if not emails:
                continue
            emoji = {
                "自媒体合作": "自媒体",
                "招聘求职": "招聘",
                "工作邮件": "工作",
                "社交通知": "社交",
                "推广营销": "推广",
                "其他": "其他"
            }.get(cat, "其他")

            cat_emails = ""
            for email in emails[:5]:
                from_email = email.get('from_email', '')
                mailto_link = f"mailto:{from_email}?subject=Re:{email['subject']}"

                cat_emails += f'''
                <div style="padding: 10px 0; border-bottom: 1px dashed #eee;">
                    <div style="margin-bottom: 4px;">
                        <a href="{mailto_link}" style="font-weight: 500; color: #1976d2; text-decoration: none;">{email['subject'][:50]}</a>
                    </div>
                    <div style="font-size: 12px; color: #999;">
                        {email['from'][:35]} · {email['date'][:16]}
                    </div>
                </div>'''

            if emails:
                category_html += f'''
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #1a1a1a; font-size: 14px; margin: 0 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid #43a047;">
                        {emoji} {cat} ({len(emails)}封)
                    </h3>
                    {cat_emails}
                    <a href="mailto:" style="font-size: 12px; color: #1976d2; text-decoration: none;">查看全部 {cat} 邮件 →</a>
                </div>'''

        html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>日报 - {today}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #43a047 0%, #2e7d32 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .stats {{ display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap; }}
        .stats span {{ background: rgba(255,255,255,0.2); padding: 5px 12px; border-radius: 15px; font-size: 13px; }}
        .section {{ background: white; padding: 25px; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .section h2 {{ margin: 0 0 20px 0; color: #1a1a1a; font-size: 18px; padding-bottom: 10px; border-bottom: 2px solid #43a047; }}
        .todo-section {{ border-left: 4px solid #e53935; }}
        .todo-section h2 {{ border-bottom-color: #e53935; }}
        ul {{ list-style: none; padding: 0; margin: 0; }}
        .highlight-box {{ background: #fff3e0; border: 2px solid #ff9800; border-radius: 10px; padding: 15px; margin-bottom: 20px; }}
        .highlight-box h3 {{ margin: 0 0 10px 0; color: #e65100; font-size: 16px; }}
        .highlight-box ul {{ margin: 0; padding-left: 20px; }}
        .highlight-box li {{ color: #333; margin-bottom: 5px; }}
        .notes {{ background: #fffde7; padding: 15px; border-radius: 8px; border-left: 4px solid #fdd835; margin-top: 20px; }}
        .notes h3 {{ margin: 0 0 10px 0; color: #333; font-size: 14px; }}
        .notes textarea {{ width: 100%; height: 80px; border: none; background: transparent; resize: none; font-family: inherit; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
        .batch-actions {{ background: #f5f5f5; padding: 12px 15px; border-radius: 8px; margin-bottom: 15px; display: flex; gap: 10px; align-items: center; }}
        .batch-actions span {{ font-size: 13px; color: #666; }}
    </style>
    <script>
        function markAsRead(emailId, btnElement) {{
            fetch('/mark-read/' + encodeURIComponent(emailId))
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        btnElement.style.background = '#43a047';
                        btnElement.textContent = '已标记';
                        btnElement.disabled = true;
                        const li = btnElement.closest('li');
                        const status = li.querySelector('.read-status');
                        if (status) status.style.display = 'inline';
                        // 勾选checkbox
                        const checkbox = li.querySelector('input[type="checkbox"]');
                        if (checkbox) checkbox.checked = true;
                    }} else {{
                        alert('标记失败: ' + data.message);
                    }}
                }})
                .catch(err => {{
                    alert('请求失败，请确保日报服务器正在运行');
                }});
        }}

        function markAllAsRead() {{
            const buttons = document.querySelectorAll('.todo-section button[onclick^="markAsRead"]');
            buttons.forEach((btn, index) => {{
                setTimeout(() => {{
                    if (btn.disabled) return;
                    const li = btn.closest('li');
                    const checkbox = li.querySelector('input[type="checkbox"]');
                    const emailId = li.dataset.emailId;
                    fetch('/mark-read/' + encodeURIComponent(emailId))
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                btn.style.background = '#43a047';
                                btn.textContent = '已标记';
                                btn.disabled = true;
                                if (checkbox) checkbox.checked = true;
                                const status = li.querySelector('.read-status');
                                if (status) status.style.display = 'inline';
                            }}
                        }})
                        .catch(err => {{}});
                }}, index * 300);
            }});
        }}
    </script>
</head>
<body>
    <div class="header">
        <h1>工作日报</h1>
        <p>{today}</p>
        <div class="stats">
            <span>{len(self.emails)} 封邮件</span>
            <span>{len(self.todos)} 项待办</span>
            <span>{len(self.categories.get("自媒体合作", []))} 商务合作</span>
        </div>
    </div>

    <div class="section todo-section">
        <h2>待办事项</h2>
        <div class="batch-actions">
            <button onclick="markAllAsRead()" style="background: #e53935; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; cursor: pointer;">一键已读全部</button>
            <span>点击后自动将所有待办邮件标记为已读</span>
        </div>
        <ul>{todo_rows}</ul>
    </div>

    <div class="highlight-box">
        <h3>重点关注：自媒体平台商务合作</h3>
        <ul>
            <li>抖音、小红书、B站、快手、微博等平台合作邀约</li>
            <li>达人/KOC/KOL商务合作洽谈</li>
            <li>品牌投放、种草、带货合作</li>
        </ul>
    </div>

    <div class="section">
        <h2>邮件分类</h2>
        {category_html if category_html else '<div style="color: #999; text-align: center; padding: 20px;">暂无邮件</div>'}
    </div>

    <div class="section">
        <div class="notes">
            <h3>备注</h3>
            <textarea placeholder="如有需要可在此添加备注..."></textarea>
        </div>
    </div>

    <div class="footer">
        由日报助理自动生成
    </div>
</body>
</html>'''

        return html_template

    def _send_email(self, html_content):
        """发送HTML日报邮件"""
        smtp_server = self.config.get("smtp_server", "smtp.163.com")
        smtp_port = 465
        smtp_user = self.config.get("email", "")
        smtp_password = self.config.get("password", "")
        recipient = self.config.get("email", "")

        if not smtp_user or not smtp_password:
            print("[Email] Email config incomplete")
            return False

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            subject = f"工作日报 {today} ({len(self.todos)}项待办)"

            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = smtp_user
            msg['To'] = recipient

            plain_text = f"工作日报 - {today}\n\n{len(self.todos)}项待办事项\n\n请查看HTML版本获取完整内容。"
            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            print(f"[Email] Sending to {recipient}...")
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient, msg.as_string())

            print("[Email] Sent successfully!")
            return True
        except Exception as e:
            print(f"[Email] Failed: {str(e)}")
            return False

    def save_report(self, tasks=None):
        """保存日报"""
        output_folder = self.config.get("output_folder",
            os.path.join(os.path.dirname(__file__), "output"))

        today = datetime.now().strftime("%Y-%m-%d")
        os.makedirs(output_folder, exist_ok=True)

        html_content = self._generate_html_report(tasks)

        html_path = os.path.join(output_folder, f"daily_report_{today}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"日报已保存到: {html_path}")
        self._send_email(html_content)
        return html_path

    def run(self, tasks=None):
        """运行日报生成"""
        try:
            self.get_emails()
            path = self.save_report(tasks)
            return 0
        except Exception as e:
            print(f"生成日报失败: {str(e)}")
            return 1

    def start_web_server(self, html_path, port=8765):
        """启动本地Web服务器用于查看日报和处理已读操作"""
        from urllib.parse import unquote

        class ReportHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=os.path.dirname(html_path), **kwargs)

            def do_GET(self):
                if self.path.startswith('/mark-read/'):
                    # 提取邮件ID并标记为已读
                    email_id = unquote(self.path[11:])
                    report_instance = self.server.report_instance
                    success, msg = report_instance.mark_as_read(email_id)

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = json.dumps({"success": success, "message": msg})
                    self.wfile.write(response.encode())
                    return

                # 返回主页面
                if self.path == '/' or self.path == '':
                    self.path = '/' + os.path.basename(html_path)

                super().do_GET()

            def log_message(self, format, *args):
                # 简化日志
                if '/mark-read/' not in str(args[0]):
                    print(f"[Web] {args[0]}")

        # 动态创建带report_instance引用的Handler类
        HandlerClass = type('DynamicHandler', (ReportHandler,), {
            'server': type('ServerObj', (), {'report_instance': self})
        })
        HandlerClass.server.report_instance = self

        self.server = HTTPServer(('localhost', port), HandlerClass)
        url = f"http://localhost:{port}"
        print(f"\n==========================================")
        print(f"本地日报服务器已启动")
        print(f"请在浏览器打开: {url}")
        print(f"按 Ctrl+C 停止服务器")
        print(f"==========================================\n")

        # 自动打开浏览器
        webbrowser.open(url)

        self.server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="日报生成器")
    parser.add_argument("--config", default="config/email_config.json",
                        help="配置文件路径")
    parser.add_argument("--tasks", nargs="*", help="今日任务列表")
    parser.add_argument("--serve", action="store_true",
                        help="启动本地Web服务器查看日报并标记已读")
    parser.add_argument("--port", type=int, default=8765,
                        help="本地服务器端口 (默认8765)")

    args = parser.parse_args()

    report = DailyReport(args.config)

    if args.serve:
        # 先生成日报
        report.get_emails()
        html_path = report.save_report()
        # 启动Web服务器
        report.start_web_server(html_path, args.port)
        return 0
    else:
        return report.run(args.tasks)


if __name__ == "__main__":
    sys.exit(main())
