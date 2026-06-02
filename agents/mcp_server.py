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
    "ai-news": {
        "module": "news.ai_news.server",
        "class": "AINewsServer",
        "methods": {
            "generate": "生成AI新闻早报",
            "test": "测试搜索"
        }
    },
    "media-manager": {
        "module": "media_manager.server",
        "class": "MediaManager",
        "methods": {
            "scan": "扫描NAS媒体文件",
            "classify": "分类媒体文件",
            "search": "搜索媒体",
            "stats": "获取统计信息"
        }
    },
    "code-review": {
        "module": "engineering_agent.server",
        "class": "CodeReviewAgent",
        "methods": {
            "review": "审查代码质量和安全性",
            "checklist": "查看审查清单"
        }
    },
    "video-subtitle": {
        "module": "video_subtitle.mcp_server",
        "class": "VideoSubtitleMCPServer",
        "methods": {
            "download_and_transcribe": "下载视频并生成字幕",
            "download_transcribe_and_proofread": "下载视频、语音识别、文案校对、生成字幕",
            "list_subtitles": "列出字幕文件"
        }
    },
    "file-converter": {
        "module": "file_converter.server",
        "class": "FileConverter",
        "methods": {
            "merge_pdfs": "合并多个PDF文件",
            "merge_images_to_pdf": "将多张图片合并为PDF",
            "merge_images_to_jpg": "将多张图片合并为JPG"
        }
    },
    "allergy-news-daily": {
        "module": "allergy_news_daily.server",
        "class": "AllergyNewsDaily",
        "methods": {
            "generate": "生成过敏诊所新闻日报",
            "load_news": "加载新闻数据"
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
            result = getattr(instance, method_name)(**arguments)
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