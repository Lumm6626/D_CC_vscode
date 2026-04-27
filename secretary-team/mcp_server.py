#!/usr/bin/env python3
"""
MCP服务包装器 - 将命令行工具转换为MCP服务
支持tools/call和initialize命令
"""

import sys
import json
import subprocess

# 服务映射
SERVICES = {
    "feishu-sync": {
        "module": "feishu_sync.server",
        "class": "FeishuSync",
        "methods": {
            "sync": "同步飞书文档",
            "test": "测试连接"
        }
    },
    "news-daily": {
        "module": "news_daily.server",
        "class": "NewsDaily",
        "methods": {
            "generate": "生成新闻早报",
            "test": "测试搜索"
        }
    },
    "daily-report": {
        "module": "daily_report.server",
        "class": "DailyReport",
        "methods": {
            "generate": "生成日报",
            "check": "检查未回复邮件"
        }
    },
    "review-agent": {
        "module": "review_agent.server",
        "class": "ReviewAgent",
        "methods": {
            "questions": "获取复盘问题",
            "generate": "生成复盘文档"
        }
    }
}


def handle_initialize():
    """处理MCP初始化请求"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "secretary-team",
            "version": "1.0.0"
        }
    }


def handle_list_tools():
    """列出所有可用工具"""
    tools = []
    for name, service in SERVICES.items():
        for method, desc in service["methods"].items():
            tools.append({
                "name": f"{name}_{method}",
                "description": f"{service['class']}: {desc}",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            })
    return tools


def handle_call_tool(name, arguments):
    """调用工具"""
    parts = name.split("_", 1)
    if len(parts) != 2:
        return {"error": "Invalid tool name"}

    service_name = parts[0]
    method_name = parts[1]

    if service_name not in SERVICES:
        return {"error": f"Unknown service: {service_name}"}

    service = SERVICES[service_name]

    try:
        # 动态导入模块
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        module = __import__(service["module"], fromlist=[service["class"]])
        cls = getattr(module, service["class"])
        instance = cls()

        # 调用方法
        if hasattr(instance, method_name):
            result = getattr(instance, method_name)()
            return {"result": result}
        else:
            return {"error": f"Method {method_name} not found"}
    except Exception as e:
        return {"error": str(e)}


def main():
    """MCP服务主循环"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            msg_id = request.get("id")

            result = None

            if method == "initialize":
                result = handle_initialize()
            elif method == "tools/list":
                result = {"tools": handle_list_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = {"content": [{"type": "text", "text": str(handle_call_tool(tool_name, tool_args))}]}
            else:
                result = {"error": f"Unknown method: {method}"}

            response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
            print(json.dumps(response), flush=True)

        except Exception as e:
            error_response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()