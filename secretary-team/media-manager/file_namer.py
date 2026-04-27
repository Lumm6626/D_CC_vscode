#!/usr/bin/env python3
"""
AI文件命名器 - 根据内容自动生成文件名
"""

import re
import os
from datetime import datetime
from typing import Dict, Optional, List


class FileNamer:
    def __init__(self, config: Dict):
        self.config = config
        self.naming_config = config.get("naming", {})
        self.pattern = self.naming_config.get("pattern", "{scene}_{date}_{index}_{keywords}.{ext}")
        self.date_format = self.naming_config.get("date_format", "%Y%m%d")
        self.max_keywords_length = self.naming_config.get("max_keywords_length", 50)

    def generate_name(self, scene: str, keywords: str = None, index: int = 1,
                      original_name: str = None, file_ext: str = None) -> str:
        """
        生成新文件名

        Args:
            scene: 场景名称
            keywords: 关键词（如产品名）
            index: 序号
            original_name: 原文件名（用于提取关键词）
            file_ext: 文件扩展名

        Returns:
            生成的新文件名
        """
        # 清理场景名称（移除"测评推荐"等后缀用于命名）
        clean_scene = self._clean_scene_name(scene)

        # 获取文件扩展名
        if file_ext is None and original_name:
            file_ext = os.path.splitext(original_name)[1].lower()
        if file_ext is None:
            file_ext = ".mp4"

        # 生成关键词
        name_keywords = self._generate_keywords(scene, keywords, original_name, clean_scene)

        # 格式化日期
        date_str = datetime.now().strftime(self.date_format)

        # 格式化序号
        index_str = f"{index:03d}"

        # 组合新文件名
        new_name = self.pattern.format(
            scene=clean_scene,
            date=date_str,
            index=index_str,
            keywords=name_keywords,
            ext=file_ext.lstrip('.')
        )

        # 清理文件名中的非法字符
        new_name = self._sanitize_filename(new_name)

        return new_name

    def _clean_scene_name(self, scene: str) -> str:
        """清理场景名称用于文件名"""
        # 移除"测评推荐"等后缀
        for suffix in ["测评推荐", "测评", "推荐"]:
            scene = scene.replace(suffix, "")

        # 如果清理后为空，返回默认
        if not scene.strip():
            return "未分类"

        return scene.strip()

    def _generate_keywords(self, scene: str, keywords: str = None,
                          original_name: str = None, clean_scene: str = None) -> str:
        """生成文件名中的关键词部分"""
        # 如果直接提供了关键词
        if keywords:
            # 截断过长的关键词
            if len(keywords) > self.max_keywords_length:
                keywords = keywords[:self.max_keywords_length - 3] + "..."
            return keywords

        # 从原文件名提取关键词
        if original_name:
            extracted = self._extract_keywords_from_name(original_name)
            if extracted:
                return extracted

        # 从场景名推断关键词
        if clean_scene:
            return clean_scene

        return "素材"

    def _extract_keywords_from_name(self, filename: str) -> Optional[str]:
        """从原文件名中提取关键词"""
        # 移除扩展名
        name = os.path.splitext(filename)[0]

        # 移除常见后缀
        patterns_to_remove = [
            r'\[.*?\]', r'【.*?】',  # 括号内容
            r'\(.*?\)',  # 圆括号内容
            r'_.*?$', r'-.*?$',  # 下划线/连字符后的内容
            r'\d{4,}',  # 长数字串
            r'[_-]+\d+$',  # 序号
        ]

        for pattern in patterns_to_remove:
            name = re.sub(pattern, '', name)

        # 分割成词
        words = re.split(r'[-_～~｜|\s]+', name)
        words = [w for w in words if len(w) >= 2 and not w.isdigit()]

        if words:
            # 取前几个有意义的词
            keywords = ''.join(words[:3])
            if len(keywords) > self.max_keywords_length:
                keywords = keywords[:self.max_keywords_length]
            return keywords

        return None

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # Windows非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)

        # 移除控制字符
        filename = re.sub(r'[\x00-\x1f]', '', filename)

        # 移除多余空格
        filename = re.sub(r'\s+', '_', filename)

        # 限制长度（Windows路径最大255）
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200 - len(ext)] + ext

        return filename

    def generate_batch_names(self, scene: str, count: int,
                            keywords: str = None, original_names: List[str] = None) -> List[str]:
        """
        批量生成文件名

        Args:
            scene: 场景名称
            count: 生成数量
            keywords: 共同关键词
            original_names: 原文件名列表

        Returns:
            生成的文件名列表
        """
        names = []
        for i in range(1, count + 1):
            original = original_names[i - 1] if original_names and i <= len(original_names) else None
            name = self.generate_name(
                scene=scene,
                keywords=keywords,
                index=i,
                original_name=original
            )
            names.append(name)

        return names

    def validate_name(self, filename: str) -> Dict:
        """
        验证文件名是否合法

        Returns:
            验证结果字典
        """
        result = {
            "valid": True,
            "errors": []
        }

        if not filename:
            result["valid"] = False
            result["errors"].append("文件名为空")
            return result

        # 检查长度
        if len(filename) > 200:
            result["valid"] = False
            result["errors"].append("文件名过长（超过200字符）")

        # 检查非法字符
        illegal_chars = r'[<>:"|?*]'
        found_illegal = re.findall(illegal_chars, filename)
        if found_illegal:
            result["valid"] = False
            result["errors"].append(f"包含非法字符: {found_illegal}")

        # 检查是否为保留设备名
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            result["valid"] = False
            result["errors"].append(f"文件名是系统保留名: {name_without_ext}")

        return result

    def get_suggested_name(self, scene: str, original_name: str = None) -> str:
        """
        根据场景和原文件名获取建议的文件名

        Args:
            scene: 场景名称
            original_name: 原文件名

        Returns:
            建议的文件名
        """
        keywords = None
        if original_name:
            keywords = self._extract_keywords_from_name(original_name)

        return self.generate_name(
            scene=scene,
            keywords=keywords,
            index=1,
            original_name=original_name
        )
