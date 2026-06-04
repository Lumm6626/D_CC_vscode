#!/usr/bin/env python3
"""
US Allergy Clinics Market Brief - 启动脚本
独立运行市场简报生成和邮件发送，方便调试和定时任务调用。
"""

import os
import sys

# Ensure we can import from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import AllergyNewsDaily


def main():
    import argparse

    parser = argparse.ArgumentParser(description="US过敏诊所市场简报生成器")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)", default=None)
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    args = parser.parse_args()

    report = AllergyNewsDaily()
    result = report.generate_market_brief(args.date, send_email=not args.no_email)

    if "error" in result:
        print(f"[Error] {result['error']}")
        sys.exit(1)

    print(f"[完成] 市场简报生成成功!")
    print(f"  - Markdown: {result.get('markdown_path', 'N/A')}")
    print(f"  - JSON: {result.get('json_path', 'N/A')}")
    print(f"  - HTML: {result.get('html_path', 'N/A')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
