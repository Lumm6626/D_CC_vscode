#!/usr/bin/env python3
"""
日报助理 MCP 服务入口
"""

from server import DailyReport
import json
import sys


def handle_request(request_data):
    """处理MCP请求"""
    command = request_data.get("command", "generate")
    tasks = request_data.get("tasks", [])

    report = DailyReport()

    if command == "generate":
        report.get_unread_emails()
        path = report.save_report(tasks)
        return {"status": "success", "file": path, "email_count": len(report.unread_emails)}
    elif command == "check":
        report.get_unread_emails()
        return {"status": "success", "emails": report.unread_emails}
    else:
        return {"status": "error", "message": f"未知命令: {command}"}


if __name__ == "__main__":
    request = json.load(sys.stdin)
    result = handle_request(request)
    print(json.dumps(result))