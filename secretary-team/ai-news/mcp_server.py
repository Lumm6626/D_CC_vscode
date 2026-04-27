#!/usr/bin/env python3
"""
新闻助理 MCP 服务入口
"""

from server import NewsDaily
import json
import sys


def handle_request(request_data):
    """处理MCP请求"""
    command = request_data.get("command", "generate")

    news = NewsDaily()

    if command == "generate":
        news.search_ai_news()
        folder = news.save_report()
        return {"status": "success", "folder": folder, "count": len(news.news_data)}
    elif command == "test":
        news.search_ai_news()
        return {"status": "success", "count": len(news.news_data)}
    else:
        return {"status": "error", "message": f"未知命令: {command}"}


if __name__ == "__main__":
    request = json.load(sys.stdin)
    result = handle_request(request)
    print(json.dumps(result))