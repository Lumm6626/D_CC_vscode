#!/usr/bin/env python3
"""
飞书助理 MCP 服务入口
"""

from server import FeishuSync
import json
import sys

def handle_request(request_data):
    """处理MCP请求"""
    command = request_data.get("command", "sync")

    sync = FeishuSync()

    if command == "sync":
        result = sync.sync_docs()
        return {"status": "success", "synced_count": result}
    elif command == "test":
        success = sync.get_access_token()
        docs = sync.get_docs_list() if success else []
        return {"status": "success" if success else "error", "docs_count": len(docs)}
    else:
        return {"status": "error", "message": f"未知命令: {command}"}

if __name__ == "__main__":
    # 从stdin读取请求
    request = json.load(sys.stdin)
    result = handle_request(request)
    print(json.dumps(result))