#!/usr/bin/env python3
"""
Code Review Agent
审查代码质量、逻辑正确性、安全漏洞、代码风格
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path


class CodeReviewAgent:
    """代码审核Agent - 审查代码质量和安全性"""

    REVIEW_CHECKLIST = [
        ("安全漏洞", [
            "SQL注入风险（是否使用参数化查询）",
            "XSS漏洞（是否对用户输入做转义）",
            "敏感信息硬编码（密码、API Key、Token）",
            "命令注入风险（subprocess调用是否安全）",
            "路径遍历风险（文件操作是否校验路径）",
            "权限校验缺失（是否有未授权访问风险）",
        ]),
        ("代码质量", [
            "函数长度是否合理（建议<50行）",
            "圈复杂度是否过高",
            "是否有重复代码",
            "变量命名是否清晰有意义",
            "是否有未使用的import或变量",
            "错误处理是否完善",
        ]),
        ("逻辑正确性", [
            "边界条件是否处理（空值、零值、极限值）",
            "循环终止条件是否正确",
            "并发安全问题（多线程/异步）",
            "资源是否正确释放（文件句柄、连接）",
            "类型转换是否安全",
        ]),
        ("最佳实践", [
            "是否符合项目代码风格",
            "是否有足够的注释和文档",
            "是否遵循SOLID原则",
            "是否有单元测试",
            "依赖是否合理（无过度依赖）",
        ]),
    ]

    def __init__(self):
        self.agent_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.agent_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def load_prompt(self):
        """加载审查系统提示"""
        prompt_file = os.path.join(self.agent_dir, "CLAUDE.md")
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def scan_files(self, target_path):
        """扫描目标路径下的代码文件"""
        code_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs',
                          '.java', '.c', '.cpp', '.h', '.css', '.html', '.sql'}
        files = []

        if os.path.isfile(target_path):
            ext = os.path.splitext(target_path)[1].lower()
            if ext in code_extensions:
                files.append(target_path)
        elif os.path.isdir(target_path):
            for root, dirs, filenames in os.walk(target_path):
                # 跳过常见非代码目录
                dirs[:] = [d for d in dirs if d not in {
                    '__pycache__', '.git', 'node_modules', 'venv', '.venv',
                    'dist', 'build', '.next', 'output'
                }]
                for f in filenames:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in code_extensions:
                        files.append(os.path.join(root, f))

        return files

    def analyze_file(self, filepath):
        """分析单个文件"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            return {"file": filepath, "error": str(e), "lines": 0, "issues": []}

        lines = content.split('\n')
        issues = []

        # 快速静态检查
        content_lower = content.lower()

        # 敏感信息检查
        sensitive_patterns = [
            ('password', '可能包含硬编码密码'),
            ('api_key', '可能包含硬编码API Key'),
            ('secret', '可能包含硬编码密钥'),
            ('token', '可能包含硬编码Token'),
            ('sk-', '疑似OpenAI/DeepSeek API Key'),
        ]
        for pattern, desc in sensitive_patterns:
            if pattern in content_lower and 'os.environ' not in content_lower and 'os.getenv' not in content_lower:
                # 检查是否是赋值语句
                for i, line in enumerate(lines, 1):
                    if pattern in line.lower() and '=' in line and not line.strip().startswith('#'):
                        if 'getenv' not in line and 'environ' not in line:
                            issues.append({
                                "line": i,
                                "severity": "high",
                                "category": "安全漏洞",
                                "issue": f"{desc}: {line.strip()[:80]}"
                            })
                            break

        # SQL注入检查
        sql_patterns = ['execute(', 'executemany(']
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if any(p in line_stripped for p in sql_patterns):
                if '?' not in line_stripped and '%s' not in line_stripped and ':' not in line_stripped:
                    if '+' in line_stripped or 'f"' in line_stripped or "f'" in line_stripped or '.format(' in line_stripped:
                        issues.append({
                            "line": i,
                            "severity": "high",
                            "category": "安全漏洞",
                            "issue": f"可能的SQL注入风险: {line_stripped[:80]}"
                        })

        # 命令注入检查
        for i, line in enumerate(lines, 1):
            if 'subprocess' in line or 'os.system' in line or 'os.popen' in line:
                if 'shell=True' in line:
                    issues.append({
                        "line": i,
                        "severity": "high",
                        "category": "安全漏洞",
                        "issue": f"shell=True 可能导致命令注入: {line.strip()[:80]}"
                    })

        # 异常处理检查
        for i, line in enumerate(lines, 1):
            if line.strip() == 'except:' or line.strip().startswith('except:'):
                issues.append({
                    "line": i,
                    "severity": "medium",
                    "category": "代码质量",
                    "issue": "裸except语句，应指定具体异常类型"
                })

        # 过长函数检查 (简单估算)
        func_lines = []
        in_func = False
        func_start = 0
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('def '):
                if in_func:
                    func_lines.append((func_start, i - 1))
                in_func = True
                func_start = i
        if in_func:
            func_lines.append((func_start, len(lines)))

        for start, end in func_lines:
            length = end - start + 1
            if length > 100:
                issues.append({
                    "line": start,
                    "severity": "low",
                    "category": "代码质量",
                    "issue": f"函数过长 ({length}行)，建议拆分"
                })

        return {
            "file": filepath,
            "lines": len(lines),
            "issues": issues,
            "size_bytes": len(content.encode('utf-8'))
        }

    def review(self, target_path):
        """执行代码审查"""
        files = self.scan_files(target_path)

        if not files:
            print(f"[Code Review] 未找到代码文件: {target_path}")
            return {"error": "No code files found", "files": [], "results": []}

        print(f"[Code Review] 扫描到 {len(files)} 个代码文件")
        results = []
        total_issues = 0
        high_issues = 0

        for f in files:
            result = self.analyze_file(f)
            results.append(result)
            total_issues += len(result.get("issues", []))
            high_issues += sum(1 for i in result.get("issues", []) if i["severity"] == "high")
            rel_path = os.path.relpath(f, target_path) if os.path.isdir(target_path) else os.path.basename(f)
            issue_count = len(result.get("issues", []))
            if issue_count > 0:
                print(f"  {rel_path}: {issue_count} 个问题")

        # 生成报告
        report = self.generate_report(target_path, results, total_issues, high_issues)

        print(f"\n[Code Review] 完成: {total_issues} 个问题 ({high_issues} 高危)")

        return {
            "target": target_path,
            "files_scanned": len(files),
            "total_issues": total_issues,
            "high_severity": high_issues,
            "results": results,
            "report_path": report
        }

    def generate_report(self, target_path, results, total_issues, high_issues):
        """生成审查报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.output_dir, f"code_review_{timestamp}.md")

        target_name = os.path.basename(target_path.rstrip('/\\'))

        lines = [
            f"# Code Review Report",
            f"",
            f"**目标**: `{target_path}`",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**文件数**: {len(results)}",
            f"**问题总数**: {total_issues} ({high_issues} 高危)",
            f"",
            f"---",
            f"",
            f"## 概览",
            f"",
            f"| 文件 | 行数 | 问题数 |",
            f"|------|------|--------|",
        ]

        for r in results:
            rel = os.path.basename(r.get("file", ""))
            lines.append(f"| {rel} | {r.get('lines', 0)} | {len(r.get('issues', []))} |")

        lines.append("")

        # 按严重程度列出问题
        for severity, label in [("high", "高危问题"), ("medium", "中等问题"), ("low", "低优先级")]:
            sev_issues = []
            for r in results:
                for issue in r.get("issues", []):
                    if issue["severity"] == severity:
                        sev_issues.append((r["file"], issue))

            if sev_issues:
                lines.append(f"## {label}")
                lines.append("")
                for filepath, issue in sev_issues:
                    rel = os.path.basename(filepath)
                    lines.append(f"- **[{issue['category']}]** `{rel}:{issue['line']}` — {issue['issue']}")
                lines.append("")

        lines.append("---")
        lines.append(f"*由 Code Review Agent 自动生成*")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return report_path


def main():
    parser = argparse.ArgumentParser(description="Code Review Agent - 代码审查")
    parser.add_argument("--path", "-p", required=True, help="要审查的文件或目录路径")
    parser.add_argument("--checklist", action="store_true", help="显示审查清单")
    args = parser.parse_args()

    agent = CodeReviewAgent()

    if args.checklist:
        print("Code Review 检查清单:\n")
        for category, items in agent.REVIEW_CHECKLIST:
            print(f"## {category}")
            for item in items:
                print(f"  - [ ] {item}")
            print()
        return

    target = os.path.abspath(args.path)
    if not os.path.exists(target):
        print(f"错误: 路径不存在: {target}")
        sys.exit(1)

    result = agent.review(target)
    if "report_path" in result:
        print(f"\n报告已保存: {result['report_path']}")


if __name__ == "__main__":
    main()
