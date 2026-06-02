#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文案库每日同步脚本
将 D:\D_CC_vscode\self-media\文案库\文案输出 同步到 L:\sata1-18501755656\LY自媒体\内容选题\文案输出
- 通过 修改时间 + 文件大小 比较判断是否需要同步
- 只同步有变化的文件
- 完成后发送邮件通知
"""

import os
import sys
import shutil
import json
import smtplib
import time
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "news_config.json")

SRC_DIR = r"D:\D_CC_vscode\self-media\文案库\文案输出"
DST_DIR = r"L:\sata1-18501755656\LY自媒体\内容选题\文案输出"

# 日志
LOG_FILE = os.path.join(BASE_DIR, "sync_copywriter.log")

def log(msg):
    """打印并记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass

def load_email_config():
    """加载邮件配置"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def need_sync(src_file, dst_file):
    """
    判断文件是否需要同步
    比较修改时间和文件大小
    """
    if not os.path.exists(dst_file):
        return True

    src_stat = os.stat(src_file)
    dst_stat = os.stat(dst_file)

    # 比较修改时间和大小
    if src_stat.st_mtime != dst_stat.st_mtime or src_stat.st_size != dst_stat.st_size:
        return True
    return False

def sync_folders(src, dst, log_func=log):
    """
    同步两个文件夹
    只复制有变化的文件
    返回: (copied_count, skipped_count, errors)
    """
    if not os.path.exists(src):
        log_func(f"[ERROR] Source folder not found: {src}")
        return 0, 0, [f"Source not found: {src}"]

    # 创建目标文件夹（如果不存在）
    os.makedirs(dst, exist_ok=True)

    copied = 0
    skipped = 0
    errors = []

    try:
        for root, dirs, files in os.walk(src):
            # 计算相对路径
            rel_root = os.path.relpath(root, src)
            if rel_root == ".":
                rel_root = ""

            dst_root = os.path.join(dst, rel_root) if rel_root else dst

            # 确保目标子目录存在
            os.makedirs(dst_root, exist_ok=True)

            for filename in files:
                src_file = os.path.join(root, filename)
                dst_file = os.path.join(dst_root, filename)

                try:
                    if need_sync(src_file, dst_file):
                        shutil.copy2(src_file, dst_file)
                        log_func(f"[COPY] {filename}")
                        copied += 1
                    else:
                        log_func(f"[SKIP] {filename} (no change)")
                        skipped += 1
                except Exception as e:
                    log_func(f"[ERROR] {filename}: {str(e)}")
                    errors.append(f"{filename}: {str(e)}")
    except Exception as e:
        log_func(f"[ERROR] Sync failed: {str(e)}")
        errors.append(str(e))

    return copied, skipped, errors

def try_windows_toast(title, message):
    """尝试发送Windows Toast通知"""
    try:
        from winotify import Notification
        notif = Notification(
            app_id="文案库同步",
            title=title,
            msg=message,
            duration="long"
        )
        notif.show()
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"[Toast] Failed: {str(e)}")
        return False

def send_email_notification(title, body, email_config):
    """发送普通邮件通知"""
    if not email_config:
        print("[EMAIL] No email config found")
        return False

    smtp_server = email_config.get("smtp_server", "smtp.163.com")
    smtp_port = email_config.get("smtp_port", 465)
    smtp_user = email_config.get("smtp_user", "")
    smtp_password = email_config.get("smtp_password", "")
    recipient = email_config.get("recipient_email", "")

    if not smtp_user or not recipient:
        print("[EMAIL] Email config incomplete")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(title, 'utf-8')
        msg['From'] = smtp_user
        msg['To'] = recipient

        plain_text = body
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
                .content {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .footer {{ text-align: center; color: #999; margin-top: 20px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                <pre>{body}</pre>
            </div>
            <div class="footer">
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        print(f"[EMAIL] Sending to {recipient}...")
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient, msg.as_string())

        print("[EMAIL] Sent successfully!")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed: {str(e)}")
        return False

def diagnose_sync_issues(src, dst):
    """
    诊断同步问题，返回可能的原因列表
    """
    issues = []

    # 1. 检查源文件夹
    if not os.path.exists(src):
        issues.append(f"❌ 源文件夹不存在: {src}")
    else:
        issues.append(f"✓ 源文件夹正常: {src}")
        # 检查是否有读取权限
        try:
            test_file = os.path.join(src, os.listdir(src)[0]) if os.listdir(src) else None
            if test_file:
                with open(test_file, 'rb') as f:
                    f.read(1)
            issues.append("✓ 源文件夹可读")
        except Exception as e:
            issues.append(f"⚠ 源文件夹读取权限异常: {str(e)}")

    # 2. 检查目标文件夹
    dst_parent = os.path.dirname(dst)
    if not os.path.exists(dst_parent):
        issues.append(f"❌ 目标父文件夹不存在: {dst_parent}")
    else:
        issues.append(f"✓ 目标父文件夹正常: {dst_parent}")
        # 检查写入权限
        try:
            test_file = os.path.join(dst_parent, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            issues.append("✓ 目标父文件夹可写")
        except Exception as e:
            issues.append(f"⚠ 目标文件夹写入权限异常: {str(e)}")

    # 3. 检查磁盘空间
    try:
        import shutil as sh
        total, used, free = shutil.disk_usage(dst_parent)
        free_gb = free / (1024**3)
        issues.append(f"✓ 目标磁盘可用空间: {free_gb:.1f} GB")
        if free_gb < 0.5:
            issues.append(f"⚠ 磁盘空间较低，仅 {free_gb:.1f} GB")
    except Exception as e:
        issues.append(f"⚠ 无法检查磁盘空间: {str(e)}")

    # 4. 检查网络路径连通性（如果是网络路径）
    if dst.startswith("\\\\") or dst.startswith("//"):
        issues.append("⚠ 网络路径检测未实现")

    return issues

def send_failure_notification(error_type, error_msg, details, email_config):
    """
    发送失败通知邮件，包含详细原因和修复建议
    """
    if not email_config:
        print("[EMAIL] No email config found")
        return False

    smtp_server = email_config.get("smtp_server", "smtp.163.com")
    smtp_port = email_config.get("smtp_port", 465)
    smtp_user = email_config.get("smtp_user", "")
    smtp_password = email_config.get("smtp_password", "")
    recipient = email_config.get("recipient_email", "")

    if not smtp_user or not recipient:
        print("[EMAIL] Email config incomplete")
        return False

    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 根据错误类型提供修复建议
    fix_suggestions = {
        "source_not_found": "请检查源文件夹是否存在，或者检查文件是否被移动/重命名",
        "access_denied": "请以管理员权限运行脚本，或检查文件夹权限设置",
        "disk_full": "请清理目标磁盘空间，删除不需要的文件",
        "network_error": "请检查网络连接，或确认目标服务器是否可用",
        "unknown": "请查看详细错误信息，或手动运行脚本进行调试"
    }

    suggestion = fix_suggestions.get(error_type, fix_suggestions["unknown"])

    body = f"""⚠️ 文案库同步失败

时间: {today}
错误类型: {error_type}

错误信息:
{error_msg}

诊断详情:
{details}

修复建议:
{suggestion}

请及时处理，或联系技术支持。
"""

    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #f44336 0%, #e91e63 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .content {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .error-box {{ background: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 15px 0; }}
            .diagnostic {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0; font-family: monospace; white-space: pre-wrap; }}
            .suggestion {{ background: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 15px 0; }}
            .footer {{ text-align: center; color: #999; margin-top: 20px; font-size: 12px; }}
            .label {{ font-weight: bold; color: #333; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⚠️ 文案库同步失败</h1>
            <p>{today}</p>
        </div>
        <div class="content">
            <div class="error-box">
                <div class="label">错误类型:</div>
                <div>{error_type}</div>
            </div>
            <div class="error-box">
                <div class="label">错误信息:</div>
                <div>{error_msg}</div>
            </div>
            <div class="diagnostic">
                <div class="label">诊断详情:</div>
{details}
            </div>
            <div class="suggestion">
                <div class="label">修复建议:</div>
                <div>{suggestion}</div>
            </div>
        </div>
        <div class="footer">
            <p>请及时处理，或联系技术支持</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(f"⚠️ [失败] 文案库同步 - {error_type}", 'utf-8')
        msg['From'] = smtp_user
        msg['To'] = recipient

        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        print(f"[EMAIL] Sending failure notification to {recipient}...")
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient, msg.as_string())

        print("[EMAIL] Failure notification sent!")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send failure notification: {str(e)}")
        return False
    """发送邮件通知"""
    if not email_config:
        print("[EMAIL] No email config found")
        return False

    smtp_server = email_config.get("smtp_server", "smtp.163.com")
    smtp_port = email_config.get("smtp_port", 465)
    smtp_user = email_config.get("smtp_user", "")
    smtp_password = email_config.get("smtp_password", "")
    recipient = email_config.get("recipient_email", "")

    if not smtp_user or not recipient:
        print("[EMAIL] Email config incomplete")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(title, 'utf-8')
        msg['From'] = smtp_user
        msg['To'] = recipient

        plain_text = body
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
                .content {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .footer {{ text-align: center; color: #999; margin-top: 20px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                <pre>{body}</pre>
            </div>
            <div class="footer">
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        print(f"[EMAIL] Sending to {recipient}...")
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient, msg.as_string())

        print("[EMAIL] Sent successfully!")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("[SYNC] 文案库同步脚本")
    print("=" * 60)
    print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[SRC ] {SRC_DIR}")
    print(f"[DST ] {DST_DIR}")
    print()

    email_config = load_email_config()

    # 检查源文件夹
    if not os.path.exists(SRC_DIR):
        error_type = "source_not_found"
        error_msg = f"源文件夹不存在: {SRC_DIR}"
        print(f"[ERROR] {error_msg}")

        # 诊断并发送详细错误通知
        issues = diagnose_sync_issues(SRC_DIR, DST)
        details = "\n".join(issues)

        if email_config:
            send_failure_notification(error_type, error_msg, details, email_config)

        # 尝试Toast通知
        try_windows_toast("⚠️ 文案库同步失败", error_msg)

        return 1

    # 执行同步
    print("[SYNC] Starting sync...")
    try:
        copied, skipped, errors = sync_folders(SRC_DIR, DST_DIR)
    except Exception as e:
        # 捕获意外错误
        error_type = "sync_exception"
        error_msg = str(e)
        print(f"[ERROR] Sync exception: {error_msg}")

        issues = diagnose_sync_issues(SRC_DIR, DST)
        details = "\n".join(issues)

        if email_config:
            send_failure_notification(error_type, error_msg, details, email_config)

        try_windows_toast("⚠️ 文案库同步失败", error_msg)
        return 1

    print()
    print(f"[RESULT] Copied: {copied}, Skipped: {skipped}, Errors: {len(errors)}")

    # 准备通知内容
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if errors:
        body = f"""文案库同步完成，但有错误:

时间: {today}
源: {SRC_DIR}
目标: {DST_DIR}

结果:
- 新增/更新: {copied} 个文件
- 跳过: {skipped} 个文件
- 错误: {len(errors)} 个

错误详情:
"""
        for err in errors:
            body += f"  - {err}\n"

        title = "[警告] 文案库同步完成（有错误）"

        # 发送有错误的通知
        if email_config:
            send_email_notification(title, body, email_config)

        # 尝试Toast
        try_windows_toast(title, f"错误: {len(errors)} 个文件")
    else:
        body = f"""文案库同步完成:

时间: {today}
源: {SRC_DIR}
目标: {DST_DIR}

结果:
- 新增/更新: {copied} 个文件
- 跳过: {skipped} 个文件
- 错误: 0 个

同步完成，无错误。
"""
        title = "[完成] 文案库同步完成"

        # 发送成功通知
        if email_config:
            send_email_notification(title, body, email_config)

        # 尝试Toast
        try_windows_toast(title, f"新增/更新: {copied} 个文件")

    print()
    print("=" * 60)
    print("[DONE] Sync completed!")
    print("=" * 60)

    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())