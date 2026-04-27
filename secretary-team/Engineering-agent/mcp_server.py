#!/usr/bin/env python3
"""
复盘助理 MCP 服务入口
"""

from server import ReviewAgent
import json
import sys


def handle_request(request_data):
    """处理MCP请求"""
    command = request_data.get("command", "questions")
    date = request_data.get("date")
    answers = request_data.get("answers", [])

    agent = ReviewAgent()

    if command == "questions":
        return {"status": "success", "questions": agent.get_questions()}
    elif command == "generate":
        if not answers:
            return {"status": "error", "message": "需要提供answers参数"}
        path = agent.generate_review(answers, date)
        return {"status": "success", "file": path}
    else:
        return {"status": "error", "message": f"未知命令: {command}"}


if __name__ == "__main__":
    request = json.load(sys.stdin)
    result = handle_request(request)
    print(json.dumps(result))