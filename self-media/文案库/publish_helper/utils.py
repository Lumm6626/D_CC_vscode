"""
工具函数：文案解析、文件读取、输出格式化
"""

import re
import os
from pathlib import Path


# 文案库根目录
CONTENT_DIR = Path(__file__).resolve().parent.parent

# 领域关键词映射
CATEGORY_KEYWORDS = {
    "家居": ["家居", "装修", "床垫", "家具", "沙发", "灯", "窗帘", "地板", "墙", "卧室", "客厅"],
    "数码": ["数码", "手机", "华为", "iPhone", "电脑", "耳机", "平板", "鸿蒙", "iOS", "安卓", "APP"],
    "VLOG": ["vlog", "VLOG", "日常", "生活"],
}


def guess_category(text):
    """根据文案内容猜测所属领域"""
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[cat] = score

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "通用"
    return best


def guess_category_from_filename(filename):
    """从文件名猜测领域（命名规则：领域_博主_标题_日期）"""
    parts = filename.replace(".txt", "").split("_")
    for part in parts:
        if part in CATEGORY_KEYWORDS:
            return part
    return None


def read_article(filepath):
    """读取文案文件，返回结构化内容"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    filename = path.stem  # 不含扩展名
    category = guess_category_from_filename(filename) or guess_category(content)

    # 提取标题（通常在第一行或"标题："之后）
    title = extract_title(content)

    return {
        "filepath": str(path),
        "filename": filename,
        "category": category,
        "title_original": title,
        "content": content,
    }


def extract_title(content):
    """从文案内容中提取标题"""
    lines = [l.strip() for l in content.split("\n") if l.strip()]

    # 优先匹配 "标题：xxx" 格式
    for line in lines[:10]:
        m = re.match(r"^标题[：:]\s*(.+)", line)
        if m:
            return m.group(1).strip()

    # 其次匹配第一行（如果它很短且不像正文）
    if lines and len(lines[0]) < 80:
        return lines[0]

    # 最后取前20字
    return content[:30].replace("\n", "") + "..."


def format_output(article_info, platform_results):
    """格式化输出到控制台和文件"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"📄 文案：{Path(article_info['filepath']).name}")
    lines.append(f"🏷️  领域：{article_info['category']}")
    lines.append(f"📝 原标题：{article_info['title_original']}")
    lines.append("=" * 60)

    for pr in platform_results:
        lines.append("")
        lines.append(f"─── {pr['platform']} ───")
        lines.append(f"📌 标题：{pr['title']}")
        lines.append(f"🏷️  话题：{' '.join(pr['tags'])}")
        lines.append(f"🖼️  封面：{pr.get('cover_path', '已生成')}")
        if pr.get("suggestions"):
            lines.append(f"💡 建议：{pr['suggestions']}")

    return "\n".join(lines)


def save_report(article_info, platform_results, output_dir=None):
    """保存发布方案到文件"""
    if output_dir is None:
        output_dir = CONTENT_DIR / "发布方案"

    os.makedirs(output_dir, exist_ok=True)
    base = Path(article_info["filepath"]).stem
    outpath = output_dir / f"发布方案_{base}.txt"

    text = format_output(article_info, platform_results)
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(text)

    return str(outpath)
