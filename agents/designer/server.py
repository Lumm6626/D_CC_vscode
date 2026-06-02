#!/usr/bin/env python3
"""
Designer Agent Server
负责所有前端界面设计、图片设计、UI/UX设计
接受设计需求，加载设计系统规范，输出完整的设计上下文供LLM处理
"""

import os
import sys
import json
import argparse
from datetime import datetime


class DesignerServer:
    """设计师服务 - 前端界面设计、图片设计、UI/UX"""

    def __init__(self):
        self.agent_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.agent_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def load_prompt(self):
        """加载系统提示和设计规范"""
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

        # 加载设计token
        tokens_file = os.path.join(self.agent_dir, "design-system", "tokens.json")
        if os.path.exists(tokens_file):
            with open(tokens_file, 'r', encoding='utf-8') as f:
                tokens = json.load(f)
                prompt_parts.append(f"\n## Design Tokens\n```json\n{json.dumps(tokens, indent=2, ensure_ascii=False)}\n```")

        return "\n\n".join(prompt_parts)

    def handle_request(self, request):
        """处理设计请求"""
        prompt = self.load_prompt()

        output = {
            "agent": "Designer",
            "request": request,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "prompt_context": prompt,
        }

        # 保存到output
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in request[:50])
        output_file = os.path.join(
            self.output_dir,
            f"design_request_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}.json"
        )
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"[Designer] 已加载设计系统规范 ({len(prompt)} 字符)")
        print(f"[Designer] 请求: {request}")
        print(f"[Designer] 上下文已保存至: {output_file}")
        print(f"\n{'='*60}")
        print("设计上下文已就绪，请使用 Claude Code 加载此 agent:")
        print(f"  claude --system-prompt-file {self.agent_dir}/system-prompt.md")
        print(f"  Task: {request}")
        print(f"{'='*60}")

        return output


def main():
    parser = argparse.ArgumentParser(description="Designer Agent")
    parser.add_argument("--request", "-r", help="设计需求描述")
    parser.add_argument("--output", "-o", help="输出格式 (json|text)", default="json")
    args = parser.parse_args()

    server = DesignerServer()
    prompt = server.load_prompt()

    if args.request:
        result = server.handle_request(args.request)
        if args.output == "text":
            # 输出纯文本上下文，供LLM直接使用
            print(f"\n=== SYSTEM PROMPT ===\n{prompt}\n=== END SYSTEM PROMPT ===")
            print(f"\n=== DESIGN REQUEST ===\n{args.request}\n=== END DESIGN REQUEST ===")
    else:
        # 无请求时输出系统提示摘要
        print(f"[Designer] 设计系统已就绪")
        print(f"[Designer] 提示长度: {len(prompt)} 字符")
        print(f"[Designer] 输出目录: {server.output_dir}")
        print(f"\n使用 --request '设计需求' 来提交设计任务")


if __name__ == "__main__":
    main()
