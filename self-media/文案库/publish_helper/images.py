"""
封面图生成器

工作流程：
  1. 先生成一张竖屏主封面（9:16，用户可在此基础上修改定稿）
  2. 以定稿的主封面为原图，按各平台尺寸裁剪/缩放
  3. 自动命名保存

裁剪策略（从竖屏主封面出发）：
  9:16  → 等比缩放（竖屏全屏）
  3:4   → 裁顶部（保留全宽，截取对应高度）
  6:7   → 裁顶部
  1:1   → 居中裁正方形
  16:9  → 居中裁横屏区域 + 拉伸
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# ── 统一封面风格配色（可自行修改）──
UNIFIED_STYLE = {
    "bg_top": "#1a1a2e",
    "bg_bottom": "#16213e",
    "accent": "#e94560",
    "text_main": "#FFFFFF",
    "text_sub": "#CCCCCC",
    "text_shadow": "#000000",
    "overlay": (0, 0, 0, 80),
}

# 封面输出目录
COVER_DIR = Path(__file__).resolve().parent.parent / "封面图"


# ── 辅助函数 ──

def _find_font():
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/deng.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for fp in candidates:
        if os.path.exists(fp):
            return fp
    return None


def _create_gradient(width, height, s):
    img = Image.new("RGB", (width, height))
    r1, g1, b1 = tuple(int(s["bg_top"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    r2, g2, b2 = tuple(int(s["bg_bottom"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    for y in range(height):
        r = int(r1 + (r2 - r1) * y / height)
        g = int(g1 + (g2 - g1) * y / height)
        b = int(b1 + (b2 - b1) * y / height)
        for x in range(width):
            img.putpixel((x, y), (r, g, b))
    return img


def _add_decorations(draw, width, height, accent_hex):
    acc = accent_hex.lstrip("#")
    r, g, b = int(acc[0:2], 16), int(acc[2:4], 16), int(acc[4:6], 16)
    for i in range(3):
        radius = 40 + i * 30
        cx = width - 80 - i * 60
        cy = 60 + i * 40
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=(r, g, b, 25))
    for i in range(2):
        radius = 50 + i * 40
        cx = 60 + i * 50
        cy = height - 80 - i * 50
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=(r, g, b, 16))


def _wrap_text(text, font, max_width, draw):
    lines = []
    current = ""
    for char in text:
        test = current + char
        w = draw.textbbox((0, 0), test, font=font)[2]
        if w > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


# ── 第1步：生成竖屏主封面 ──

def generate_master(title, subtitle=None, tag=None, output_dir=None):
    """生成一张 1080×1920 (9:16) 竖屏主封面，供用户定稿"""
    s = UNIFIED_STYLE
    width, height = 1080, 1920

    img = _create_gradient(width, height, s)
    draw = ImageDraw.Draw(img, "RGBA")

    font_path = _find_font()
    if not font_path:
        raise RuntimeError("未找到中文字体")

    fs = width // 18
    font_title = ImageFont.truetype(font_path, fs * 2)
    font_sub = ImageFont.truetype(font_path, fs)
    font_tag = ImageFont.truetype(font_path, max(fs // 2, 14))

    _add_decorations(draw, width, height, s["accent"])

    # 底部遮罩
    bar_height = height // 3
    draw.rectangle([0, height - bar_height, width, height], fill=s["overlay"])

    # 左上角标签
    if tag:
        label = f"#{tag}"
        bbox = draw.textbbox((0, 0), label, font=font_tag)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad = 8
        mx, my = width // 16, width // 20
        draw.rectangle([mx, my, mx + tw + pad*2, my + th + pad*2], fill=(255, 255, 255, 25))
        draw.text((mx + pad, my + pad), label, fill=s["text_main"], font=font_tag)

    # 副标题
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        sw = bbox[2] - bbox[0]
        sx = (width - sw) // 2
        sy = height - bar_height - fs * 2
        draw.text((sx + 2, sy + 2), subtitle, fill=(0, 0, 0, 80), font=font_sub)
        draw.text((sx, sy), subtitle, fill=s["text_sub"], font=font_sub)

    # 主标题（底部居中）
    margin = width // 12
    max_text_width = width - margin * 2
    title_lines = _wrap_text(title, font_title, max_text_width, draw)
    line_height = fs * 2 + fs // 2
    total_h = len(title_lines) * line_height
    start_y = height - bar_height + (bar_height - total_h) // 2
    if subtitle:
        start_y = height - bar_height + (bar_height - total_h) // 2

    for i, line in enumerate(title_lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        y = start_y + i * line_height
        draw.text((x + 3, y + 3), line, fill=(0, 0, 0, 100), font=font_title)
        draw.text((x, y), line, fill=s["text_main"], font=font_title)

    # 保存
    if output_dir is None:
        output_dir = COVER_DIR / "主封面"
    os.makedirs(output_dir, exist_ok=True)

    safe = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:30] or "master"
    outpath = Path(output_dir) / f"主封面_{safe}.jpg"

    img.convert("RGB").save(outpath, quality=95, optimize=True)
    return str(outpath)


# ── 第2步：从主封面裁剪适配各平台尺寸 ──

def _crop_from_master(master_img, target_width, target_height):
    """
    从主封面裁剪出目标尺寸。
    裁剪策略：
      - 同比例 → 直接缩放
      - 竖屏但更方 → 裁顶部（保留全宽）
      - 正方形 → 居中裁
      - 横屏 → 居中裁横屏区域
    """
    mw, mh = master_img.size
    target_ratio = target_width / target_height
    master_ratio = mw / mh

    if abs(target_ratio - master_ratio) < 0.01:
        # 同比例，直接缩放
        return master_img.resize((target_width, target_height), Image.LANCZOS)

    if target_ratio < master_ratio:
        # 目标比例更竖长（比原图还窄）→ 裁左右
        new_w = int(round(mh * target_ratio))
        x = (mw - new_w) // 2
        cropped = master_img.crop((x, 0, x + new_w, mh))
    else:
        # 目标比例更宽（更方或横屏）→ 裁上下
        new_h = int(round(mw / target_ratio))
        if new_h >= mh:
            # 目标比原图更竖长，取满高
            return master_img.resize((target_width, target_height), Image.LANCZOS)
        y = (mh - new_h) // 2  # 居中裁
        # 但如果是 3:4 或 6:7 这样的"稍微宽一点"，裁顶部更好（文字在下方）
        if target_ratio > 0.6 and target_ratio < 0.75:
            # 3:4 (0.75) 或 6:7 (0.857) - 裁顶部保留文字
            # 实际上 9:16=0.5625, 3:4=0.75, 6:7≈0.857
            # 从顶部裁，保留底部文字区域
            y = 0
        cropped = master_img.crop((0, y, mw, y + new_h))

    return cropped.resize((target_width, target_height), Image.LANCZOS)


def adapt_all(master_path, output_dir=None, article_file=None):
    """
    从主封面生成各平台各尺寸的封面图。

    参数:
        master_path: 定稿的主封面图片路径
        output_dir: 输出目录
        article_file: 文案文件路径（用于目录命名）

    返回:
        {平台名: [{size, ratio, note, path}, ...], ...}
    """
    from platform import PLATFORMS

    if not os.path.exists(master_path):
        raise FileNotFoundError(f"主封面文件不存在: {master_path}")

    master = Image.open(master_path).convert("RGB")
    article_stem = Path(article_file).stem[:20] if article_file else "cover"

    base_dir = output_dir or (COVER_DIR / article_stem)
    os.makedirs(base_dir, exist_ok=True)

    results = {}
    for pname, cfg in PLATFORMS.items():
        platform_results = []
        for size_info in cfg["cover_sizes"]:
            w, h = size_info["size"]
            ratio = size_info["ratio"]
            note = size_info["note"]

            adapted = _crop_from_master(master, w, h)

            filename = f"{pname}_{ratio.replace(':','-')}_{article_stem}.jpg"
            outpath = Path(base_dir) / filename
            adapted.save(outpath, quality=92, optimize=True)

            platform_results.append({
                "size": f"{w}x{h}",
                "ratio": ratio,
                "note": note,
                "path": str(outpath),
            })
        results[pname] = platform_results

    return results


# ── 独立测试 ──
if __name__ == "__main__":
    m = generate_master("床垫多少钱才不交智商税？", subtitle="行内人说实话", tag="家居")
    print(f"主封面: {m}")
    out = adapt_all(m)
    for p, sizes in out.items():
        for s in sizes:
            print(f"  {p} {s['ratio']} -> {s['path']}")
