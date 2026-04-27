#!/usr/bin/env python3
"""
媒体素材管理助理 MCP 服务入口
"""

from server import MediaManager
import json
import sys


def handle_request(request_data):
    """处理MCP请求"""
    command = request_data.get("command", "")
    params = request_data.get("params", {})

    manager = MediaManager()

    try:
        if command == "check_connection":
            return manager.check_nas_connection()

        elif command == "scan_folder":
            folder_path = params.get("folder_path")
            recursive = params.get("recursive", True)
            return manager.scan_nas_folder(folder_path, recursive)

        elif command == "get_folder_structure":
            folder_path = params.get("folder_path")
            max_depth = params.get("max_depth", 3)
            return manager.get_folder_structure(folder_path, max_depth)

        elif command == "classify_file":
            return manager.classify_file(
                file_path=params.get("file_path"),
                filename=params.get("filename"),
                description=params.get("description"),
                media_id=params.get("media_id")
            )

        elif command == "classify_all":
            return manager.classify_all_pending()

        elif command == "generate_filename":
            return manager.generate_filename(
                scene=params.get("scene"),
                keywords=params.get("keywords"),
                original_name=params.get("original_name"),
                index=params.get("index", 1)
            )

        elif command == "batch_generate_names":
            return manager.batch_generate_names(
                scene=params.get("scene"),
                original_names=params.get("original_names", []),
                keywords=params.get("keywords")
            )

        elif command == "rename_and_move":
            return manager.rename_and_move_file(
                media_id=params.get("media_id"),
                new_name=params.get("new_name"),
                target_scene=params.get("target_scene")
            )

        elif command == "batch_rename":
            return manager.batch_rename_and_move(
                media_ids=params.get("media_ids"),
                scene=params.get("scene")
            )

        elif command == "search":
            return manager.search_media(
                keyword=params.get("keyword"),
                scene=params.get("scene"),
                file_type=params.get("file_type"),
                limit=params.get("limit", 100)
            )

        elif command == "get_stats":
            return manager.get_stats()

        elif command == "get_media":
            return manager.get_media_by_id(params.get("media_id"))

        elif command == "get_scene_config":
            return manager.get_scene_config()

        elif command == "update_scene_config":
            return manager.update_scene_config(params.get("scenes", []))

        elif command == "help":
            return {"help": manager.get_help()}

        else:
            return {"status": "error", "message": f"未知命令: {command}"}

    except Exception as e:
        return {"status": "error", "message": str(e), "command": command}


if __name__ == "__main__":
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError:
        # 如果没有输入，使用默认命令
        request = {"command": "help"}

    result = handle_request(request)
    print(json.dumps(result, ensure_ascii=False))
