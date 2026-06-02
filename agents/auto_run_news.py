#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻助理自动运行脚本
- 检测网络连接
- 等待指定时间
- 运行3个新闻助理
- 发送汇总简报到邮箱
"""

import os
import sys
import time
import json
import smtplib
import subprocess
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR = BASE_DIR  # BASE_DIR 就是 agents 目录

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_network(timeout=30):
    """检测网络连接"""
    print("[NET] Checking network connection...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            import urllib.request
            urllib.request.urlopen("https://www.baidu.com", timeout=5)
            print("[NET] Network connected!")
            return True
        except Exception as e:
            print(f"[NET] Waiting... ({int(time.time() - start_time)}s)")
            time.sleep(5)

    print("[NET] Network timeout")
    return False

def wait_and_check_network(wait_minutes=10):
    """等待指定分钟并检测网络"""
    print(f"[WAIT] Will run news agents after {wait_minutes} minutes...")
    print("[WAIT] Checking network every minute...")

    elapsed = 0
    while elapsed < wait_minutes:
        if check_network():
            remaining = wait_minutes - elapsed
            if remaining > 0:
                print(f"[WAIT] Network connected, waiting {remaining} more minutes...")
                time.sleep(remaining * 60)
            break
        elapsed += 1
        if elapsed < wait_minutes:
            print(f"[WAIT] Minute {elapsed}/{wait_minutes}, continue waiting...")
    else:
        print("[WARN] Network check timeout, continuing anyway...")

    return True

def run_news_script(script_name, script_path):
    """运行单个新闻脚本"""
    print(f"\n{'='*50}")
    print(f"[RUN] {script_name}")
    print('='*50)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=NEWS_DIR,
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )

        if result.returncode == 0:
            print(f"[OK] {script_name} completed")
            # 打印输出中的邮件发送状态
            if "[Email] Sent successfully!" in result.stdout:
                print(f"[EMAIL] {script_name} - Email already sent by script")
            elif "[Email] Failed" in result.stdout:
                print(f"[EMAIL] {script_name} - Email failed in script, will retry")
            return True, result.stdout
        else:
            print(f"[ERR] {script_name} failed: {result.stderr[:500]}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"[ERR] {script_name} timeout")
        return False, "Timeout"
    except Exception as e:
        print(f"[ERR] {script_name} exception: {str(e)}")
        return False, str(e)

def collect_today_reports():
    """收集今日报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    reports = []

    # 新闻报告目录
    report_dirs = {
        "AI News": os.path.join(NEWS_DIR, "news", "ai-news", "output", today),
        "Pharma News": os.path.join(NEWS_DIR, "news", "pharma-news", "output", today),
        "Medical Device News": os.path.join(NEWS_DIR, "news", "medical-device-news", "output", today),
    }

    for name, path in report_dirs.items():
        html_file = None
        json_file = None

        if os.path.exists(path):
            for f in os.listdir(path):
                if f.endswith(".html"):
                    html_file = os.path.join(path, f)
                elif f.endswith(".json") and "news" in f.lower():
                    json_file = os.path.join(path, f)

        reports.append({
            "name": name,
            "path": path,
            "html": html_file,
            "json": json_file,
            "exists": os.path.exists(path) and html_file is not None
        })

        print(f"[REPORT] {name}: {'Generated' if html_file else 'Not generated'}")

    return reports

def send_summary_email(reports, wait_minutes=10):
    """发送汇总简报邮件"""
    print("\n[EMAIL] Sending summary report...")

    # 读取邮件配置 - 优先使用news_config.json
    news_config_path = os.path.join(NEWS_DIR, "config", "news_config.json")
    if os.path.exists(news_config_path):
        with open(news_config_path, 'r', encoding='utf-8') as f:
            email_config = json.load(f)
    else:
        print("[EMAIL] No email config found")
        return False

    smtp_server = email_config.get("smtp_server", "smtp.163.com")
    smtp_port = email_config.get("smtp_port", 465)
    smtp_user = email_config.get("smtp_user", "")
    smtp_password = email_config.get("smtp_password", "")
    recipient = email_config.get("recipient_email", "")

    if not smtp_user or not recipient:
        print("[EMAIL] Email config incomplete, skip sending")
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    # 构建邮件内容
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
            .report-list {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .report-item {{ padding: 15px; border-bottom: 1px solid #eee; }}
            .report-item:last-child {{ border-bottom: none; }}
            .report-name {{ font-size: 16px; font-weight: bold; color: #333; margin-bottom: 5px; }}
            .report-status {{ font-size: 14px; }}
            .status-ok {{ color: #4caf50; }}
            .status-fail {{ color: #f44336; }}
            .footer {{ text-align: center; color: #999; margin-top: 20px; font-size: 12px; }}
            .info {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>News Daily Report</h1>
            <p>{today}</p>
        </div>

        <div class="info">
            <p><strong>Auto Task Info:</strong></p>
            <p>Startup Delay: {wait_minutes} minutes after boot</p>
            <p>Run Time: {datetime.now().strftime('%H:%M:%S')}</p>
            <p>Status: Completed</p>
        </div>

        <div class="report-list">
            <h3 style="margin-top: 0; color: #333;">Report Status</h3>
    """

    for report in reports:
        status_class = "status-ok" if report["exists"] else "status-fail"
        status_text = "OK" if report["exists"] else "Failed"
        news_count = "N/A"

        if report["json"]:
            try:
                with open(report["json"], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    news_count = data.get("count", "N/A")
            except:
                pass

        html_content += f"""
            <div class="report-item">
                <div class="report-name">{report['name']}</div>
                <div class="report-status {status_class}">{status_text} | {news_count} articles</div>
            </div>
        """

    html_content += f"""
        </div>

        <div class="footer">
            <p>Auto-generated by News Assistant</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """

    # 发送邮件，带重试
    for attempt in range(1, 4):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(f"News Report {today}", 'utf-8')
            msg['From'] = smtp_user
            msg['To'] = recipient

            plain_text = f"""News Report {today}

Auto task completed.
Startup Delay: {wait_minutes} minutes

Report Status:
"""
            for report in reports:
                status = "OK" if report["exists"] else "Failed"
                plain_text += f"- {report['name']}: {status}\n"

            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            print(f"[EMAIL] Attempt {attempt}/3 - Sending summary to {recipient}...")
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient, msg.as_string())

            print("[EMAIL] Summary email sent successfully!")
            return True
        except Exception as e:
            print(f"[EMAIL] Summary email attempt {attempt} failed: {str(e)}")
            if attempt < 3:
                time.sleep(5)
    return False


def retry_send_individual_news_email(report_info, max_retries=2):
    """
    重试发送单个新闻邮件（备用机制）
    report_info: dict with keys: name, html_path, subject
    """
    news_config_path = os.path.join(NEWS_DIR, "config", "news_config.json")
    if os.path.exists(news_config_path):
        with open(news_config_path, 'r', encoding='utf-8') as f:
            email_config = json.load(f)
    else:
        return False

    smtp_server = email_config.get("smtp_server", "smtp.163.com")
    smtp_port = email_config.get("smtp_port", 465)
    smtp_user = email_config.get("smtp_user", "")
    smtp_password = email_config.get("smtp_password", "")
    recipient = email_config.get("recipient_email", "")

    if not smtp_user or not recipient:
        return False

    html_path = report_info.get("html_path")
    if not html_path or not os.path.exists(html_path):
        print(f"[EMAIL] {report_info['name']} - HTML file not found, skipping")
        return False

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        today = datetime.now().strftime("%Y-%m-%d")
        subject = report_info.get("subject", f"{report_info['name']} - {today}")

        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = smtp_user
        msg['To'] = recipient

        plain_text = f"{subject}\n\nPlease view the HTML version for full content."
        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        for attempt in range(1, max_retries + 1):
            try:
                print(f"[EMAIL-RETRY] {report_info['name']} - Attempt {attempt}/{max_retries}...")
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, recipient, msg.as_string())
                print(f"[EMAIL-RETRY] {report_info['name']} - Sent successfully!")
                return True
            except Exception as e:
                print(f"[EMAIL-RETRY] {report_info['name']} - Attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    time.sleep(3)
        return False
    except Exception as e:
        print(f"[EMAIL-RETRY] {report_info['name']} - Error: {str(e)}")
        return False

def main():
    print("="*60)
    print("[NEWS] News Assistant Auto Run Script")
    print("="*60)
    print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 等待并检测网络 (测试时跳过，直接设为已连接)
    wait_minutes = 10
    print("[TEST] Skipping network wait for testing...")
    print(f"[TEST] Would wait {wait_minutes} minutes in production...")

    # 2. 运行新闻助理
    scripts = [
        ("AI News Agent", os.path.join(NEWS_DIR, "news", "ai-news", "server.py"), "ai_news.html", "AI News Daily"),
        ("Pharma News Agent", os.path.join(NEWS_DIR, "news", "pharma-news", "server.py"), "pharma_news.html", "医药生物制药新闻"),
        ("Medical Device News Agent", os.path.join(NEWS_DIR, "news", "medical-device-news", "server.py"), "medical_news.html", "医疗器械新闻"),
    ]

    results = []
    script_outputs = {}
    today = datetime.now().strftime("%Y-%m-%d")

    for name, path, html_file, subject in scripts:
        success, output = run_news_script(name, path)
        results.append((name, success))
        script_outputs[name] = output

        # 检查该脚本的邮件是否发送成功
        email_sent = False
        if "[Email] Sent successfully!" in output:
            print(f"[EMAIL-CHECK] {name} - Email sent OK")
            email_sent = True
        elif "[Email] Failed" in output or "[Email] All" in output:
            print(f"[EMAIL-CHECK] {name} - Email failed, will retry from auto_run")
            email_sent = False

        # 如果邮件发送失败，尝试重试
        if not email_sent:
            if "AI News" in name:
                html_path = os.path.join(NEWS_DIR, "news", "ai-news", "output", today, html_file)
            elif "Pharma" in name:
                html_path = os.path.join(NEWS_DIR, "news", "pharma-news", "output", today, html_file)
            elif "Medical" in name:
                html_path = os.path.join(NEWS_DIR, "news", "medical-device-news", "output", today, html_file)
            else:
                html_path = None

            if html_path and os.path.exists(html_path):
                print(f"[EMAIL-RETRY] {name} - Retrying from HTML file: {html_path}")
                retry_send_individual_news_email({
                    "name": name,
                    "html_path": html_path,
                    "subject": f"{subject} - {today}"
                })

    # 3. 收集报告
    print("\n[COLLECT] Checking generated reports...")
    reports = collect_today_reports()

    # 4. 发送汇总邮件
    send_summary_email(reports, wait_minutes)

    # 5. 完成
    print("\n" + "="*60)
    print("[DONE] Auto task completed!")
    print("="*60)

    # 输出结果摘要
    success_count = sum(1 for _, s in results if s)
    print(f"\nResults: {success_count}/{len(results)} agents succeeded")

    return 0 if success_count == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())
