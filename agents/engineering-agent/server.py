#!/usr/bin/env python3
"""
复盘助理 (review-agent)
功能：引导式对话深挖，生成反思文档
"""

import json
import os
import sys
import argparse
from datetime import datetime


class ReviewAgent:
    def __init__(self, config_path="config/review_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.conversation_history = []

    def _load_config(self):
        """加载配置文件"""
        config_file = os.path.join(os.path.dirname(__file__), "..", self.config_path)
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_questions(self):
        """获取引导问题"""
        return [
            "今天工作/生活中最让你有成就感的事情是什么？",
            "今天遇到了什么挑战或困难？你是如何应对的？",
            "今天有什么事情让你感到困惑或需要反思？",
            "如果重新来过，你会做出什么不同的选择？",
            "今天学到了什么重要的经验或教训？"
        ]

    def generate_review(self, answers, date=None):
        """生成反思文档"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        output_folder = self.config.get("output_folder",
            os.path.join(os.path.dirname(__file__), "output"))
        os.makedirs(output_folder, exist_ok=True)

        # 读取当天日报（如果有）
        daily_report_folder = self.config.get("daily_report_folder", "")
        daily_content = ""
        if daily_report_folder:
            report_path = os.path.join(daily_report_folder, f"daily_report_{date}.md")
            if os.path.exists(report_path):
                with open(report_path, 'r', encoding='utf-8') as f:
                    daily_content = f.read()

        # 构建对话记录
        dialogue_record = ""
        for i, (q, a) in enumerate(zip(self.get_questions(), answers), 1):
            dialogue_record += f"""
### Q{i}: {q}

**A{i}**: {a}

"""

        # 构建反思模板
        md_template = f"""# 每日复盘 - {date}

## 📋 当日概况

{daily_content if daily_content else "（无当日日报记录）"}

## 💬 对话记录

{dialogue_record}

## 🔍 深度分析

_（根据上述对话，自动生成分析）_

### 成就与收获
_从第一题回答中提炼_

### 挑战与成长
_从第二、三题回答中提炼_

### 改进方向
_从第四题回答中提炼_

### 核心洞察
_从第五题回答中提炼_

---

## 🌟 明日行动

_（建议下一步行动）_

1.
2.
3.

---

*由复盘助理自动生成 | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        # 保存文件
        md_path = os.path.join(output_folder, f"review_{date}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_template)

        # 保存JSON
        json_path = os.path.join(output_folder, f"review_{date}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "date": date,
                "questions": self.get_questions(),
                "answers": answers,
                "daily_content": daily_content
            }, f, ensure_ascii=False, indent=2)

        print(f"反思文档已保存到: {md_path}")
        return md_path

    def start_review(self, date=None):
        """开始复盘对话"""
        questions = self.get_questions()
        print(f"\n{'='*50}")
        print("🌙 开始每日复盘")
        print(f"{'='*50}\n")

        answers = []
        for i, q in enumerate(questions, 1):
            print(f"\n问题 {i}/5: {q}")
            print("> ", end="")
            answer = input().strip()
            answers.append(answer if answer else "（未作答）")

        print("\n正在生成反思文档...")
        path = self.generate_review(answers, date)

        print("\n✅ 复盘完成！")
        return path


def main():
    parser = argparse.ArgumentParser(description="复盘助理")
    parser.add_argument("--config", default="config/review_config.json",
                        help="配置文件路径")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--interactive", action="store_true",
                        help="交互式对话模式")

    args = parser.parse_args()

    agent = ReviewAgent(args.config)

    if args.interactive:
        return agent.start_review(args.date)
    else:
        # 非交互模式，打印引导问题
        questions = agent.get_questions()
        print("复盘引导问题：")
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q}")
        return 0


if __name__ == "__main__":
    sys.exit(main())