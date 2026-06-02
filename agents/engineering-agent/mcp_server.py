#!/usr/bin/env python3
"""
Code Review Agent MCP 服务入口
"""

from server import CodeReviewAgent
import json
import sys


def handle_request(request_data):
    """处理MCP请求"""
    command = request_data.get("command", "review")
    path = request_data.get("path")

    if not path:
        return {"status": "error", "message": "需要提供path参数（文件或目录路径）"}

    agent = CodeReviewAgent()

    if command == "review":
        result = agent.review(path)
        return {"status": "success", **result}
    elif command == "checklist":
        checklist = []
        for category, items in agent.REVIEW_CHECKLIST:
            checklist.append({"category": category, "items": items})
        return {"status": "success", "checklist": checklist}
    else:
        return {"status": "error", "message": f"未知命令: {command}"}


if __name__ == "__main__":
    request = json.load(sys.stdin)
    result = handle_request(request)
    print(json.dumps(result, ensure_ascii=False))
