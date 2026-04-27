#!/usr/bin/env python3
"""
场景分类器 - 根据关键词匹配对媒体文件进行场景分类
"""

import re
from typing import List, Dict, Optional, Tuple


class SceneClassifier:
    def __init__(self, scenes: List[Dict]):
        """
        初始化场景分类器

        Args:
            scenes: 场景配置列表，每项包含 name, keywords, target_folder
        """
        self.scenes = scenes
        self._build_keyword_map()

    def _build_keyword_map(self):
        """构建关键词到场景的映射"""
        self.keyword_to_scene = {}
        for scene in self.scenes:
            for keyword in scene.get("keywords", []):
                # 关键词转小写用于匹配
                self.keyword_to_scene[keyword.lower()] = scene["name"]

    def classify(self, filename: str, description: str = None) -> Tuple[str, float]:
        """
        对文件进行场景分类

        Args:
            filename: 文件名
            description: 可选的描述信息

        Returns:
            (场景名称, 置信度)
        """
        # 合并文件名和描述进行匹配
        text = (filename + " " + (description or "")).lower()

        scores = {}
        for scene in self.scenes:
            scene_name = scene["name"]
            keywords = scene.get("keywords", [])

            score = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword.lower() in text:
                    score += 1
                    matched_keywords.append(keyword)

            if score > 0:
                # 计算置信度（匹配关键词数量 / 总关键词数量）
                confidence = min(score / len(keywords) * 2, 1.0)
                scores[scene_name] = (confidence, matched_keywords)

        if not scores:
            return ("未分类", 0.0)

        # 返回得分最高的场景
        best_scene = max(scores.items(), key=lambda x: x[1][0])
        return (best_scene[0], best_scene[1][0])

    def classify_with_details(self, filename: str, description: str = None) -> Dict:
        """
        对文件进行场景分类，返回详细信息

        Returns:
            包含分类结果和匹配详情的字典
        """
        text = (filename + " " + (description or "")).lower()

        results = []
        for scene in self.scenes:
            scene_name = scene["name"]
            keywords = scene.get("keywords", [])

            matched = []
            for keyword in keywords:
                if keyword.lower() in text:
                    matched.append(keyword)

            if matched:
                confidence = min(len(matched) / len(keywords) * 2, 1.0)
                results.append({
                    "scene": scene_name,
                    "confidence": confidence,
                    "matched_keywords": matched,
                    "target_folder": scene.get("target_folder", scene_name)
                })

        if not results:
            return {
                "scene": "未分类",
                "confidence": 0.0,
                "matched_keywords": [],
                "target_folder": "未分类"
            }

        # 按置信度排序
        results.sort(key=lambda x: x["confidence"], reverse=True)
        best = results[0]

        return {
            "scene": best["scene"],
            "confidence": best["confidence"],
            "matched_keywords": best["matched_keywords"],
            "target_folder": best["target_folder"],
            "all_matches": results
        }

    def get_scene_by_name(self, scene_name: str) -> Optional[Dict]:
        """根据名称获取场景配置"""
        for scene in self.scenes:
            if scene["name"] == scene_name:
                return scene
        return None

    def get_target_folder(self, scene_name: str) -> str:
        """获取场景对应的目标文件夹"""
        scene = self.get_scene_by_name(scene_name)
        if scene:
            return scene.get("target_folder", scene_name)
        return "未分类"

    def get_all_scenes(self) -> List[str]:
        """获取所有场景名称"""
        return [scene["name"] for scene in self.scenes]

    def extract_keywords_from_filename(self, filename: str) -> List[str]:
        """
        从文件名中提取可能的关键词

        Args:
            filename: 文件名

        Returns:
            提取的关键词列表
        """
        # 移除扩展名
        name = re.sub(r'\.[^.]+$', '', filename)

        # 移除常见分隔符周围的内容
        separators = ['_', '-', ' ', '～', '~', '｜', '|', '【', '】', '[', ']']
        for sep in separators:
            name = name.replace(sep, ' ')

        # 分割成词组
        words = name.split()

        # 过滤太短的词和纯数字
        keywords = [w for w in words if len(w) >= 2 and not w.isdigit()]

        return keywords

    def suggest_category_for_keywords(self, keywords: List[str]) -> List[Dict]:
        """
        根据关键词建议可能的分类

        Args:
            keywords: 关键词列表

        Returns:
            可能的分类列表
        """
        text = ' '.join(keywords).lower()

        suggestions = []
        for scene in self.scenes:
            matched = [kw for kw in scene.get("keywords", []) if kw.lower() in text]
            if matched:
                suggestions.append({
                    "scene": scene["name"],
                    "target_folder": scene.get("target_folder", scene["name"]),
                    "matched_keywords": matched,
                    "confidence": len(matched) / len(scene.get("keywords", []))
                })

        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions
