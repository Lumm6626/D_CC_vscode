#!/usr/bin/env python3
"""
媒体素材管理助理 (MediaManager)

功能：
1. 自动命名文件 - AI根据内容/场景自动命名
2. 场景分类整理 - 按「美食探店」「旅行Vlog」「产品测评」等分类
3. 素材搜索查找 - 通过关键词搜索素材
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from database import MediaDatabase
from nas_accessor import NASAccessor
from scene_classifier import SceneClassifier
from file_namer import FileNamer


class MediaManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "config", "media_config.json"
            )

        self.config_path = config_path
        self.config = self._load_config()

        # 初始化各组件
        self.db = MediaDatabase(self.config.get("database", {}).get("path"))
        self.nas = NASAccessor(self.config)
        self.classifier = SceneClassifier(self.config.get("scenes", []))
        self.namer = FileNamer(self.config)

        # 确保输出目录存在
        output_dir = os.path.join(os.path.dirname(__file__), "output", "logs")
        os.makedirs(output_dir, exist_ok=True)

    def _load_config(self) -> Dict:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_config(self):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    # ==================== NAS操作 ====================

    def check_nas_connection(self) -> Dict:
        """检查NAS连接状态"""
        connected = self.nas.check_connection()
        return {
            "connected": connected,
            "root_path": self.nas._get_nas_root(),
            "message": "连接正常" if connected else "无法访问NAS，请检查映射驱动器"
        }

    def scan_nas_folder(self, folder_path: str = None, recursive: bool = True) -> Dict:
        """扫描NAS文件夹"""
        files = self.nas.scan_folder(folder_path, recursive)

        # 添加到数据库
        scan_batch = datetime.now().strftime("%Y%m%d%H%M%S")
        added_count = 0

        for file_info in files:
            try:
                media_id = self.db.add_media_file(
                    file_path=file_info["path"],
                    filename=file_info["name"],
                    file_type=file_info["ext"],
                    file_size=file_info["size"],
                    scan_batch=scan_batch
                )
                added_count += 1
            except Exception as e:
                print(f"[MediaManager] 添加文件失败: {str(e)}")

        return {
            "total_found": len(files),
            "added_to_db": added_count,
            "scan_batch": scan_batch,
            "files": files[:10]  # 返回前10个示例
        }

    def get_folder_structure(self, folder_path: str = None, max_depth: int = 3) -> Dict:
        """获取文件夹结构"""
        return self.nas.get_folder_structure(folder_path, max_depth)

    # ==================== 场景分类 ====================

    def classify_file(self, file_path: str = None, filename: str = None,
                     description: str = None, media_id: int = None) -> Dict:
        """对文件进行场景分类"""
        if media_id:
            media = self.db.get_media_by_id(media_id)
            if media:
                file_path = media["original_path"]
                filename = media["filename"]

        if not filename and file_path:
            filename = os.path.basename(file_path)

        if not filename:
            return {"error": "未提供文件名"}

        # 执行分类
        result = self.classifier.classify_with_details(filename, description)

        # 更新数据库
        if media_id:
            self.db.update_media_info(media_id, scene_category=result["scene"])
        elif file_path:
            media = self.db.get_media_by_path(file_path)
            if media:
                self.db.update_media_info(media["id"], scene_category=result["scene"])

        return result

    def classify_all_pending(self) -> Dict:
        """对所有待分类文件进行分类"""
        pending = self.db.get_pending_files(limit=1000)
        classified = 0

        for media in pending:
            result = self.classifier.classify(media["filename"])
            self.db.update_media_info(
                media["id"],
                scene_category=result[0]
            )
            classified += 1

        return {
            "total_pending": len(pending),
            "classified": classified
        }

    def update_scene_config(self, scenes: List[Dict]):
        """更新场景配置"""
        self.config["scenes"] = scenes
        self._save_config()
        self.classifier = SceneClassifier(scenes)
        self.db.save_scene_config(scenes)
        return {"status": "success", "scenes": scenes}

    def get_scene_config(self) -> List[Dict]:
        """获取场景配置"""
        return self.config.get("scenes", [])

    # ==================== 文件命名 ====================

    def generate_filename(self, scene: str, keywords: str = None,
                         original_name: str = None, index: int = 1) -> Dict:
        """生成新文件名"""
        file_ext = None
        if original_name:
            file_ext = os.path.splitext(original_name)[1]

        new_name = self.namer.generate_name(
            scene=scene,
            keywords=keywords,
            index=index,
            original_name=original_name,
            file_ext=file_ext
        )

        # 验证文件名
        validation = self.namer.validate_name(new_name)

        return {
            "original_name": original_name,
            "generated_name": new_name,
            "scene": scene,
            "keywords": keywords,
            "index": index,
            "validation": validation
        }

    def batch_generate_names(self, scene: str, original_names: List[str],
                            keywords: str = None) -> List[Dict]:
        """批量生成文件名"""
        results = []
        for i, original in enumerate(original_names, 1):
            result = self.generate_filename(
                scene=scene,
                keywords=keywords,
                original_name=original,
                index=i
            )
            results.append(result)

        return results

    # ==================== 文件重命名与移动 ====================

    def rename_and_move_file(self, media_id: int, new_name: str = None,
                            target_scene: str = None) -> Dict:
        """重命名并移动文件到对应场景文件夹"""
        media = self.db.get_media_by_id(media_id)
        if not media:
            return {"error": "文件不存在", "media_id": media_id}

        # 确定新文件名
        if not new_name:
            new_name = self.namer.generate_name(
                scene=target_scene or media["scene_category"],
                original_name=media["filename"]
            )

        # 确定目标文件夹
        if not target_scene and media["scene_category"]:
            target_scene = media["scene_category"]

        target_folder = self.classifier.get_target_folder(target_scene or "未分类")

        # 构建目标路径
        nas_root = self.nas._get_nas_root()
        target_dir = os.path.join(nas_root, target_folder)
        target_path = os.path.join(target_dir, new_name)

        # 移动文件
        success = self.nas.move_file(media["original_path"], target_path)

        if success:
            # 更新数据库
            self.db.mark_as_renamed(media_id, new_name, target_path)
            self.db.add_naming_history(
                media_id,
                media["filename"],
                new_name,
                "rule"
            )

            return {
                "status": "success",
                "old_path": media["original_path"],
                "new_path": target_path,
                "new_name": new_name
            }
        else:
            return {
                "status": "error",
                "message": "文件移动失败",
                "media_id": media_id
            }

    def batch_rename_and_move(self, media_ids: List[int] = None,
                             scene: str = None) -> Dict:
        """批量重命名并移动文件"""
        if media_ids:
            files = [self.db.get_media_by_id(mid) for mid in media_ids]
        else:
            files = self.db.get_pending_files(scene=scene, limit=100)

        results = []
        for i, media in enumerate(files):
            if not media:
                continue

            new_name = self.namer.generate_name(
                scene=media["scene_category"] or scene,
                original_name=media["filename"],
                index=i + 1
            )

            result = self.rename_and_move_file(media["id"], new_name)
            results.append(result)

        success_count = sum(1 for r in results if r.get("status") == "success")

        return {
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
            "results": results
        }

    # ==================== 搜索功能 ====================

    def search_media(self, keyword: str = None, scene: str = None,
                    file_type: str = None, limit: int = 100) -> List[Dict]:
        """搜索媒体文件"""
        return self.db.search_media(keyword, scene, file_type, limit)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_stats = self.db.get_total_stats()
        scene_stats = self.db.get_scene_stats()

        return {
            "total_files": total_stats["total"] or 0,
            "renamed_files": total_stats["renamed"] or 0,
            "unclassified_files": total_stats["unclassified"] or 0,
            "total_size_mb": round((total_stats["total_size"] or 0) / (1024 * 1024), 2),
            "scene_stats": scene_stats
        }

    def get_media_by_id(self, media_id: int) -> Optional[Dict]:
        """获取媒体文件详情"""
        return self.db.get_media_by_id(media_id)

    def get_media_by_path(self, path: str) -> Optional[Dict]:
        """获取媒体文件详情"""
        return self.db.get_media_by_path(path)

    # ==================== 帮助方法 ====================

    def get_help(self) -> str:
        """获取帮助信息"""
        return """
媒体素材管理助理 使用指南：

1. 初始化
   - 确保NAS驱动器已映射（如 Z:）
   - check_connection() 检查连接状态

2. 扫描文件
   - scan_folder() 扫描NAS文件夹
   - classify_all_pending() 分类所有待处理文件

3. 搜索文件
   - search_media(keyword="关键词") 关键词搜索
   - search_media(scene="场景名") 按场景搜索
   - get_stats() 查看统计信息

4. 重命名整理
   - generate_filename() 生成新文件名
   - batch_rename_and_move() 批量重命名并移动

5. 场景管理
   - get_scene_config() 获取场景配置
   - update_scene_config() 更新场景配置

示例：
    m = MediaManager()
    m.check_connection()
    result = m.scan_folder()
    m.classify_all_pending()
    results = m.search_media(keyword="床垫")
"""


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="媒体素材管理助理")
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--scan", action="store_true", help="扫描NAS文件夹")
    parser.add_argument("--classify", action="store_true", help="分类所有待处理文件")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--search", help="搜索关键词")

    args = parser.parse_args()

    manager = MediaManager(args.config)

    if args.scan:
        print("[*] 扫描NAS文件夹...")
        result = manager.scan_nas_folder()
        print(f"[+] 发现 {result['total_found']} 个文件")
        print(f"[+] 已添加到数据库: {result['added_to_db']} 个")

    elif args.classify:
        print("[*] 分类待处理文件...")
        result = manager.classify_all_pending()
        print(f"[+] 已分类: {result['classified']} 个文件")

    elif args.stats:
        stats = manager.get_stats()
        print(f"总文件数: {stats['total_files']}")
        print(f"已命名: {stats['renamed_files']}")
        print(f"未分类: {stats['unclassified_files']}")
        print(f"总大小: {stats['total_size_mb']} MB")

    elif args.search:
        results = manager.search_media(keyword=args.search)
        print(f"找到 {len(results)} 个结果:")
        for r in results[:10]:
            print(f"  - {r['filename']} [{r['scene_category']}]")

    else:
        print(manager.get_help())


if __name__ == "__main__":
    main()
