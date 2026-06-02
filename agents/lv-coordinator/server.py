#!/usr/bin/env python3
"""
管家LV (lv-coordinator)
功能：主Agent角色，采访式挖掘需求，主动汇报工作进展
"""

import json
import os
import sys
import subprocess
import argparse
import re
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 导入自我进化Agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from self_improving_agent.agent import SelfImprovingAgent
    SELF_IMPROVING_AVAILABLE = True
except ImportError:
    SELF_IMPROVING_AVAILABLE = False
    print("[WARN] SelfImprovingAgent not available, memory features disabled")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class WorkStatus:
    """工作状态跟踪"""
    def __init__(self, status_file="config/work_status.json"):
        self.status_file = status_file
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.status_file_path = os.path.join(self.base_dir, status_file)
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.status_file_path):
            with open(self.status_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_active": None,
            "news_last_run": None,
            "md_news_last_run": None,
            "media_scan_last_run": None,
            "pending_tasks": [],
            "completed_tasks": [],
            "user_goals": []
        }

    def save(self):
        os.makedirs(os.path.dirname(self.status_file_path), exist_ok=True)
        with open(self.status_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def update_activity(self):
        self.data["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.save()

    def update_task_status(self, task_type, status, details=""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = {"type": task_type, "status": status, "details": details, "time": now}

        if status == "completed":
            self.data["completed_tasks"].insert(0, entry)
            self.data["pending_tasks"] = [t for t in self.data["pending_tasks"] if t.get("type") != task_type]
            # 更新对应任务的最后运行时间
            if task_type == "news":
                self.data["news_last_run"] = now
            elif task_type == "md_news":
                self.data["md_news_last_run"] = now
            elif task_type == "media_scan":
                self.data["media_scan_last_run"] = now
        else:
            self.data["pending_tasks"] = [t for t in self.data["pending_tasks"] if t.get("type") != task_type]
            self.data["pending_tasks"].append(entry)

        self.save()


class LVCoordinator:
    """管家LV - 智能助手"""

    def __init__(self, config_path="config/lv_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.work_status = WorkStatus()
        # 初始化自我进化Agent
        self.self_improving_agent = None
        if SELF_IMPROVING_AVAILABLE:
            try:
                db_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "self-improving-agent", "memory.db"
                )
                self.self_improving_agent = SelfImprovingAgent(db_path)
                print(f"[MEM] SelfImprovingAgent initialized: {db_path}")
            except Exception as e:
                print(f"[WARN] Failed to initialize SelfImprovingAgent: {e}")
                self.self_improving_agent = None
        self.interview_questions = [
            {"key": "goal", "question": "您希望达成什么目标？", "desc": "了解最终目的"},
            {"key": "audience", "question": "这个需求的主要受众是谁？", "desc": "了解服务对象"},
            {"key": "priority", "question": "这件事对您来说优先级如何？", "desc": "了解重要程度"},
            {"key": "deadline", "question": "有截止日期吗？", "desc": "了解时间要求"},
            {"key": "constraints", "question": "有什么限制或顾虑吗？", "desc": "了解约束条件"},
            {"key": "success", "question": "您如何定义这件事做成功了？", "desc": "了解成功标准"},
            {"key": "history", "question": "之前有没有尝试过类似的方法？", "desc": "了解历史经验"},
            {"key": "resources", "question": "您目前有哪些资源可以用？", "desc": "了解可用资源"},
            {"key": "risks", "question": "您觉得可能会有什么风险？", "desc": "了解潜在问题"},
            {"key": "expectations", "question": "您对结果有什么预期？", "desc": "了解期望值"},
        ]
        self.current_interview = {}
        self.interview_index = 0

    def _load_config(self):
        config_file = os.path.join(os.path.dirname(__file__), "..", self.config_path)
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _run_script(self, script_path):
        """运行Python脚本"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, script_path)
        try:
            result = subprocess.run(
                [sys.executable, full_path],
                capture_output=True,
                text=True,
                timeout=180
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def greet_and_report(self):
        """问候用户并汇报工作进展"""
        print("\n" + "="*60)
        print("您好！我是LV，您的专属管家 👋")
        print("="*60)

        # 检查上次活动时间
        last_active = self.work_status.data.get("last_active")
        if last_active:
            print(f"\n上次在线: {last_active}")

        print("\n📊 工作进展汇报:")
        print("-"*40)

        # 新闻早报状态
        news_last = self.work_status.data.get("news_last_run")
        if news_last:
            print(f"  📰 AI新闻早报: 上次运行 {news_last}")
        else:
            print(f"  📰 AI新闻早报: 尚未运行")

        # 医疗器械新闻状态
        md_news_last = self.work_status.data.get("md_news_last_run")
        if md_news_last:
            print(f"  🏥 医疗器械新闻: 上次运行 {md_news_last}")
        else:
            print(f"  🏥 医疗器械新闻: 尚未运行")

        # 媒体管理状态
        media_last = self.work_status.data.get("media_scan_last_run")
        if media_last:
            print(f"  🎬 媒体管理: 上次扫描 {media_last}")
        else:
            print(f"  🎬 媒体管理: 尚未扫描")

        # 待完成任务
        pending = self.work_status.data.get("pending_tasks", [])
        if pending:
            print(f"\n  ⏳ 待完成:")
            for p in pending[:5]:
                print(f"     - {p.get('type', '未知')}: {p.get('details', '')}")

        # 最近完成
        completed = self.work_status.data.get("completed_tasks", [])
        if completed:
            print(f"\n  ✅ 最近完成:")
            for c in completed[:3]:
                print(f"     - {c.get('type', '未知')}: {c.get('details', '')}")

        print("\n" + "-"*40)

    def ask_for_help(self):
        """主动询问需要什么帮助"""
        print("\n🤔 请问有什么我可以帮您的？")
        print("\n我可以帮您：")
        print("  1. 📰 生成AI新闻早报")
        print("  2. 🏥 生成医疗器械新闻早报")
        print("  3. 🎬 扫描/管理NAS媒体文件")
        print("  4. 🔍 代码审查（安全/质量/逻辑）")
        print("  5. 🎨 Designer - 前端界面/图片设计")
        print("  6. ⚙️ Engineer - 后端功能和代码开发")
        print("  7. ❓ 告诉我您的需求，我来帮您规划")
        print("\n或者直接输入您想做的事，我来帮您安排 👇")

    def start_interview(self, initial_request):
        """开始采访模式挖掘需求"""
        print("\n" + "="*60)
        print("💡 收到需求，开始深度挖掘...")
        print("="*60)

        self.current_interview = {
            "initial_request": initial_request,
            "answers": {},
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        # 分析初始请求，提取已知信息
        request_lower = initial_request.lower()

        # 检查是否涉及具体任务
        if any(k in request_lower for k in ["新闻", "早报", "ai"]):
            self.current_interview["answers"]["has_news"] = True
        if any(k in request_lower for k in ["医疗", "器械", "医械"]):
            self.current_interview["answers"]["has_md_news"] = True
        if any(k in request_lower for k in ["媒体", "nas", "素材"]):
            self.current_interview["answers"]["has_media"] = True
        if any(k in request_lower for k in ["审查", "review", "代码"]):
            self.current_interview["answers"]["has_code_review"] = True
        if any(k in request_lower for k in ["设计", "ui", "界面", "页面"]):
            self.current_interview["answers"]["has_ui"] = True
        if any(k in request_lower for k in ["后端", "api", "接口", "开发"]):
            self.current_interview["answers"]["has_backend"] = True

        print(f"\n📝 您的需求: {initial_request}")
        print("\n为了更好地帮您，我需要了解一些信息：\n")

        # 问第一个问题
        self.ask_next_question()

    def ask_next_question(self):
        """问下一个问题"""
        if self.interview_index >= len(self.interview_questions):
            self.finish_interview()
            return

        q = self.interview_questions[self.interview_index]
        print(f"\n❓ 问题 {self.interview_index + 1}/10: {q['question']}")
        print(f"   ({q['desc']})")

        try:
            answer = input("\n您的回答: ").strip()
        except EOFError:
            answer = ""

        if answer.lower() in ["跳过", "skip", "没有了", "够了"]:
            self.current_interview["answers"][q["key"]] = "未明确"
        else:
            self.current_interview["answers"][q["key"]] = answer

        self.interview_index += 1

        if self.interview_index < len(self.interview_questions):
            self.ask_next_question()
        else:
            self.finish_interview()

    def finish_interview(self):
        """完成采访，生成行动计划"""
        print("\n" + "="*60)
        print("📋 根据您的需求，我理解如下：")
        print("="*60)

        answers = self.current_interview.get("answers", {})

        print(f"\n🎯 目标: {answers.get('goal', '未明确')}")
        print(f"👥 受众: {answers.get('audience', '未明确')}")
        print(f"⏰ 截止: {answers.get('deadline', '无固定截止')}")
        print(f"⚠️ 限制: {answers.get('constraints', '无')} ")

        # 确定要执行的任务
        tasks = []

        if answers.get("has_news"):
            tasks.append(("news", "生成AI新闻早报", "news/ai-news/server.py"))
        if answers.get("has_md_news"):
            tasks.append(("md_news", "生成医疗器械新闻早报", "news/medical-device-news/server.py"))
        if answers.get("has_media"):
            tasks.append(("media_scan", "扫描NAS媒体文件", "media-manager/server.py"))
        if answers.get("has_code_review"):
            tasks.append(("code_review", "代码审查", "engineering-agent/server.py"))
        if answers.get("has_ui"):
            tasks.append(("ui_design", "UI设计", "designer/server.py"))
        if answers.get("has_backend"):
            tasks.append(("backend_dev", "后端开发", "engineer/server.py"))

        if tasks:
            print(f"\n📌 行动计划:")
            for i, (t_type, t_desc, t_script) in enumerate(tasks, 1):
                print(f"   {i}. {t_desc}")

            print("\n是否开始执行？(y/n) ", end="")
            try:
                confirm = input().strip().lower()
            except EOFError:
                confirm = "y"

            if confirm in ["y", "yes", "是", ""]:
                self.execute_tasks(tasks)
            else:
                print("\n好的，随时可以告诉我执行。")
        else:
            print("\n📝 您的需求已记录，我会持续跟进。")

        # 重置采访状态
        self.interview_index = 0
        self.current_interview = {}
        self.work_status.update_activity()

    def execute_tasks(self, tasks):
        """执行任务列表"""
        print("\n" + "="*60)
        print("🚀 开始执行任务...")
        print("="*60 + "\n")

        for task_type, task_desc, script_path in tasks:
            print(f"\n▶ 执行: {task_desc}")
            success, output = self._run_script(script_path)

            if success:
                print(f"✅ {task_desc} 完成")
                self.work_status.update_task_status(task_type, "completed", task_desc)
                # 记录成功执行
                if self.self_improving_agent:
                    self.self_improving_agent.record_agent_execution(
                        agent_type="lv-coordinator",
                        task_type=task_type,
                        task_description=task_desc,
                        status="success",
                        output_summary=output[:500] if output else ""
                    )
            else:
                print(f"❌ {task_desc} 失败: {output[:200]}")
                self.work_status.update_task_status(task_type, "failed", task_desc)
                # 记录失败执行
                if self.self_improving_agent:
                    self.self_improving_agent.record_agent_execution(
                        agent_type="lv-coordinator",
                        task_type=task_type,
                        task_description=task_desc,
                        status="failed",
                        error_message=output[:500] if output else "Unknown error"
                    )

        print("\n" + "="*60)
        print("✅ 任务执行完成！")
        print("="*60)

    def process_request(self, user_request):
        """处理用户请求"""
        request_lower = user_request.lower().strip()

        # 记录用户对话
        if self.self_improving_agent:
            self.self_improving_agent.record_conversation(
                agent_type="lv-coordinator",
                role="user",
                content=user_request,
                metadata={"request_type": "command" if request_lower in ["1", "2", "3", "4"] else "interview"}
            )

        # 检查是否是简单命令
        if request_lower in ["1", "新闻", "早报", "ai新闻"]:
            self.execute_tasks([("news", "生成AI新闻早报", "news/ai-news/server.py")])
            return

        if request_lower in ["2", "医疗器械", "医械", "医疗新闻"]:
            self.execute_tasks([("md_news", "生成医疗器械新闻早报", "news/medical-device-news/server.py")])
            return

        if request_lower in ["3", "媒体", "nas", "素材", "扫描"]:
            self.execute_tasks([("media_scan", "扫描NAS媒体文件", "media-manager/server.py")])
            return

        if request_lower in ["4", "审查", "review", "代码审查", "code review"]:
            self.execute_tasks([("code_review", "代码审查", "engineering-agent/server.py")])
            return

        if request_lower in ["5", "设计", "ui", "界面", "页面"]:
            self.execute_tasks([("ui_design", "UI设计", "designer/server.py")])
            return

        if request_lower in ["6", "后端", "api", "接口", "开发"]:
            self.execute_tasks([("backend_dev", "后端开发", "engineer/server.py")])
            return

        # 如果是复杂需求，开启采访模式
        self.start_interview(user_request)

    def run(self, request=None):
        """运行管家"""
        if request:
            # 单次请求模式
            self.process_request(request)
        else:
            # 交互模式
            self.greet_and_report()
            self.ask_for_help()

            while True:
                try:
                    print()
                    user_input = input("您: ").strip()

                    if not user_input:
                        continue

                    if user_input.lower() in ["quit", "退出", "exit", "再见"]:
                        print("\n👋 再见！祝您工作顺利！")
                        self.work_status.update_activity()
                        break

                    # 检查是否是命令
                    if user_input in ["1", "2", "3", "4", "5", "6", "7"]:
                        commands = {
                            "1": "生成AI新闻早报",
                            "2": "生成医疗器械新闻早报",
                            "3": "扫描NAS媒体素材",
                            "4": "审查代码",
                            "5": "帮我做UI设计",
                            "6": "帮我做后端开发",
                            "7": "告诉我需求"
                        }
                        user_input = commands[user_input]

                    self.process_request(user_input)

                    # 完成后再次询问
                    print()
                    self.ask_for_help()

                except KeyboardInterrupt:
                    print("\n\n👋 再见！")
                    self.work_status.update_activity()
                    break
                except EOFError:
                    break


def main():
    parser = argparse.ArgumentParser(description="管家LV - 您的专属助手")
    parser.add_argument("--request", "-r", help="直接执行请求")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")

    args = parser.parse_args()

    lv = LVCoordinator()

    if args.request:
        lv.run(request=args.request)
    elif args.interactive:
        lv.run()
    else:
        # 默认交互模式
        lv.run()


if __name__ == "__main__":
    main()
