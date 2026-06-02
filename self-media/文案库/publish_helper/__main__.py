"""
自媒体多平台发布助手 CLI

用法:
    python -m publish_helper <文案文件路径>                   # 全流程
    python -m publish_helper <文案文件路径> --text-only        # 仅标题+话题
    python -m publish_helper <文案文件路径> --master           # 仅生成竖屏主封面
    python -m publish_helper <文案文件路径> --adapt <主封面图> # 从定稿封面裁剪各平台尺寸
    python -m publish_helper <文案文件路径> --cover-only       # 生成主封面 + 裁剪所有尺寸
    python -m publish_helper --list                            # 查看平台规则
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from platform import PLATFORMS, list_platforms
from utils import read_article, save_report, CATEGORY_KEYWORDS
from titles import full_generation, extract_keywords
from images import generate_master, adapt_all, COVER_DIR


def print_banner():
    print()
    print("  +=========================================+")
    print("  |   [自媒体多平台发布助手 v1.0]            |")
    print("  |   标题 . 话题 . 封面图 一键生成          |")
    print("  +=========================================+")
    print()


def run_text(article_info):
    """生成标题和话题标签"""
    print("[生成] 各平台标题 & 话题标签 ...\n")
    results = full_generation(article_info)
    for r in results:
        print(f"  --- {r['platform']} ---")
        print(f"    标题: {r['title']}")
        tags_str = " ".join(r['tags'][:8])
        if r['tags'][8:]:
            tags_str += "\n" + "          " + " ".join(r['tags'][8:])
        print(f"    话题: {tags_str}")
        print()
    return results


def run_master(article_info, subtitle=None):
    """生成竖屏主封面"""
    print("[主封面] 生成 1080×1920 (9:16) 竖屏主封面 ...")
    cat = article_info["category"]
    master_path = generate_master(
        title=article_info["title_original"],
        subtitle=subtitle,
        tag=cat if cat != "通用" else None,
    )
    print(f"\n  [+] 主封面已生成: {master_path}")
    print(f"\n  [提示] 你可以用 Photoshop / Canva / 美图秀秀 编辑这张图，")
    print(f"        然后运行 python -m publish_helper <文案> --adapt <编辑后的图>")
    print(f"        来自动裁剪各平台尺寸。")
    return master_path


def run_adapt(master_path, article_info, output_dir=None):
    """从定稿主封面裁剪各平台尺寸"""
    if not os.path.exists(master_path):
        print(f"[错误] 主封面文件不存在: {master_path}")
        return None

    print(f"[适配] 从主封面裁剪各平台尺寸 ...\n")
    results = adapt_all(
        master_path=master_path,
        output_dir=output_dir,
        article_file=article_info["filepath"],
    )

    for pname, size_list in results.items():
        print(f"  [{pname}]")
        for s in size_list:
            print(f"    {s['ratio']:>4s}  {s['size']:>11s}  {s['note']}")
            print(f"      -> {s['path']}")
        print()

    return results


def parse_args(args):
    """解析命令行参数"""
    filepath = None
    master_path = None
    flags = {"text": False, "master": False, "adapt": False, "cover": False, "info": False, "list": False}

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--text-only":
            flags["text"] = True
        elif a == "--master":
            flags["master"] = True
        elif a == "--adapt":
            flags["adapt"] = True
            if i + 1 < len(args) and not args[i+1].startswith("--"):
                master_path = args[i+1]
                i += 1
        elif a == "--cover-only":
            flags["cover"] = True
        elif a == "--info":
            flags["info"] = True
        elif a == "--list":
            flags["list"] = True
        elif a == "--help":
            flags["list"] = True  # show help via the --list handler
        elif not a.startswith("--"):
            filepath = a
        i += 1

    return filepath, master_path, flags


def main():
    filepath, master_path_arg, flags = parse_args(sys.argv[1:])

    # ── --list ──
    if flags["list"]:
        print_banner()
        list_platforms()
        print()
        print("[支持的内容领域]:", ", ".join(CATEGORY_KEYWORDS.keys()))
        print()
        print("[用法]")
        print("  python -m publish_helper <文案>                  # 全流程（标题+话题+封面）")
        print("  python -m publish_helper <文案> --text-only      # 仅生成标题+话题")
        print("  python -m publish_helper <文案> --master         # 仅生成竖屏主封面")
        print("  python -m publish_helper <文案> --adapt <主封面>  # 从主封面裁剪各平台")
        print("  python -m publish_helper <文案> --cover-only     # 生成主封面 + 裁剪")
        print("  python -m publish_helper <文案> --info           # 只分析文案")
        print("  python -m publish_helper --list                  # 查看本帮助")
        return

    # ── 需要文案文件 ──
    if not filepath:
        print("[错误] 请指定文案文件路径，或用 --list 查看帮助")
        return

    p = Path(filepath)
    if not p.exists():
        p2 = Path(__file__).resolve().parent.parent / filepath
        if p2.exists():
            p = p2
        else:
            print(f"[错误] 文件不存在: {filepath}")
            return

    print_banner()

    try:
        article_info = read_article(str(p))
    except FileNotFoundError as e:
        print(f"[错误] {e}")
        return

    subtitle = None  # 后续可扩展为参数

    # ── --info ──
    if flags["info"]:
        print(f"[文件] {Path(article_info['filepath']).name}")
        print(f"[领域] {article_info['category']}")
        print(f"[原标题] {article_info['title_original']}")
        print(f"[关键词] {extract_keywords(article_info['content'])}")
        return

    # 明确模式判断
    mode_text = flags["text"]
    mode_master = flags["master"]
    mode_adapt = flags["adapt"]
    mode_cover = flags["cover"]  # master + adapt

    # 全流程 = 没指定任何模式
    full = not mode_text and not mode_master and not mode_adapt and not mode_cover

    do_text = full or mode_text or mode_cover
    do_master = full or mode_master or mode_cover
    do_adapt = full or mode_adapt or mode_cover

    # ── 生成标题+话题 ──
    if do_text:
        results = run_text(article_info)
        report_path = save_report(article_info, results)
        print(f"[报告] 已保存: {report_path}\n")

    # ── 生成竖屏主封面 ──
    if do_master:
        master_path = run_master(article_info, subtitle)
        print()

    # ── 从主封面裁剪各平台 ──
    if do_adapt:
        if master_path_arg:
            mp = master_path_arg
        elif do_master:
            # 用刚生成的主封面
            safe = "".join(c for c in article_info["title_original"] if c.isalnum() or c in " _-").strip()[:30] or "master"
            mp = str(COVER_DIR / "主封面" / f"主封面_{safe}.jpg")
        elif mode_adapt:
            print("[错误] --adapt 需要指定主封面图片路径")
            print("  用法: python -m publish_helper <文案> --adapt <主封面图.jpg>")
            return
        else:
            mp = None

        if mp:
            run_adapt(mp, article_info)

    print("[完成]")


if __name__ == "__main__":
    main()
