#!/usr/bin/env python3
"""
Engineer Agent Server
负责后端后台的功能和代码开发
接受开发需求，加载技术栈规范，输出完整的开发上下文供LLM处理
"""

import os
import sys
import json
import argparse
from datetime import datetime


class EngineerServer:
    """工程师服务 - 后端功能和代码开发"""

    def __init__(self):
        self.agent_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.agent_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def load_prompt(self):
        """加载系统提示和技术规范"""
        prompt_parts = []

        # 加载 CLAUDE.md
        claude_md = os.path.join(self.agent_dir, "CLAUDE.md")
        if os.path.exists(claude_md):
            with open(claude_md, 'r', encoding='utf-8') as f:
                prompt_parts.append(f.read())

        # 加载 system-prompt.md
        system_prompt = os.path.join(self.agent_dir, "system-prompt.md")
        if os.path.exists(system_prompt):
            with open(system_prompt, 'r', encoding='utf-8') as f:
                prompt_parts.append(f.read())

        return "\n\n".join(prompt_parts)

    def handle_request(self, request):
        """处理后端开发请求"""
        prompt = self.load_prompt()

        output = {
            "agent": "Engineer",
            "request": request,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "prompt_context": prompt,
        }

        # 保存到output
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in request[:50])
        output_file = os.path.join(
            self.output_dir,
            f"dev_request_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}.json"
        )
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"[Engineer] 已加载技术栈规范 ({len(prompt)} 字符)")
        print(f"[Engineer] 请求: {request}")
        print(f"[Engineer] 上下文已保存至: {output_file}")
        print(f"\n{'='*60}")
        print("开发上下文已就绪，请使用 Claude Code 加载此 agent:")
        print(f"  claude --system-prompt-file {self.agent_dir}/system-prompt.md")
        print(f"  Task: {request}")
        print(f"{'='*60}")

        return output


def main():
    parser = argparse.ArgumentParser(description="Engineer Agent")
    parser.add_argument("--request", "-r", help="开发需求描述")
    parser.add_argument("--output", "-o", help="输出格式 (json|text)", default="json")
    args = parser.parse_args()

    server = EngineerServer()
    prompt = server.load_prompt()

    if args.request:
        result = server.handle_request(args.request)
        if args.output == "text":
            # 输出纯文本上下文，供LLM直接使用
            print(f"\n=== SYSTEM PROMPT ===\n{prompt}\n=== END SYSTEM PROMPT ===")
            print(f"\n=== DEV REQUEST ===\n{args.request}\n=== END DEV REQUEST ===")
    else:
        # 无请求时输出系统提示摘要
        print(f"[Engineer] 技术栈已就绪")
        print(f"[Engineer] 提示长度: {len(prompt)} 字符")
        print(f"[Engineer] 输出目录: {server.output_dir}")
        print(f"\n使用 --request '开发需求' 来提交开发任务")


if __name__ == "__main__":
    main()
