#!/usr/bin/env python3
"""
多平台发布秘书 (publish-agent)
功能：AI生成各平台适配的标题、描述、话题，生成一键发布包
"""

import json
import os
import sys
import argparse
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    print("错误：需要安装 requests 包")
    sys.exit(1)


class PublishAgent:
    def __init__(self, config_path="config/publish_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.client = None

    def _load_config(self):
        """加载配置文件"""
        config_file = os.path.join(os.path.dirname(__file__), "..", self.config_path)
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def init_openai(self):
        """初始化OpenAI客户端"""
        api_key = self.config.get("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
        return api_key if api_key else None

    def _call_gpt(self, prompt, system_prompt=""):
        """调用GPT生成内容"""
        api_key = self.init_openai()
        if not api_key:
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 1500
                },
                timeout=60
            )
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"GPT调用失败: {e}")
            return None

    def generate_content(self, video_info):
        """生成各平台适配内容"""
        title = video_info.get("title", "")
        description = video_info.get("description", "")
        tags = video_info.get("tags", [])
        video_type = video_info.get("type", "通用")  # 知识科普/日常vlog/产品测评/教程

        # 各平台的提示词
        system_prompt = f"""你是一个专业的社交媒体内容策划师，擅长为视频创作者生成各平台最佳适配的标题、描述和话题标签。
擅长创作吸引人的内容，让视频获得更多曝光和互动。"""

        prompt = f"""请为以下视频生成多平台发布内容：

视频标题：{title}
视频简介：{description}
视频类型：{video_type}
已有话题：{', '.join(tags)}

请为以下平台分别生成内容：

## 1. 抖音
- 标题（15字内，极具吸引力）
- 描述（开头要有悬念/冲突/共鸣，100字内）
- 话题标签（3-5个，格式：#话题名）

## 2. B站（哔哩哔哩）
- 标题（25字内，带点/括号等符号增加点击欲）
- 描述（开头要有梗/槽点，200字内）
- 话题标签（3-5个）

## 3. 小红书
- 标题（20字内，有悬念或数字）
- 正文（开头用emoji，200字内，带emoji）
- 话题标签（5-8个，带#号）

## 4. 视频号
- 标题（20字内，正能量/情感向）
- 描述（100字内，引发共鸣）
- 话题标签（3-5个）

## 5. 快手
- 标题（15字内，草根/接地气风格）
- 描述（100字内）
- 话题标签（3-5个）

请用JSON格式输出：
{{
  "douyin": {{"title": "", "description": "", "tags": []}},
  "bilibili": {{"title": "", "description": "", "tags": []}},
  "xiaohongshu": {{"title": "", "description": "", "tags": []}},
  "channels": {{"title": "", "description": "", "tags": []}},
  "kuaishou": {{"title": "", "description": "", "tags": []}}
}}
"""

        result = self._call_gpt(prompt, system_prompt)
        if not result:
            return self._fallback_generate(video_info)

        # 尝试解析JSON
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                content = json.loads(json_match.group())
                return content
        except:
            pass

        return self._fallback_generate(video_info)

    def _fallback_generate(self, video_info):
        """当GPT不可用时的备选生成"""
        title = video_info.get("title", "我的视频")
        tags = video_info.get("tags", [])

        # 简单的备选方案
        tag_str = " ".join([f"#{t}" for t in tags[:5]]) if tags else "#视频"

        return {
            "douyin": {
                "title": title[:15],
                "description": f"这个视频告诉你... {tag_str}",
                "tags": tags[:5] if tags else ["视频", "分享"]
            },
            "bilibili": {
                "title": f"【{title[:20]}】",
                "description": f"大家好，今天分享... {tag_str}",
                "tags": tags[:5] if tags else ["日常", "分享"]
            },
            "xiaohongshu": {
                "title": f"必看！{title[:18]}",
                "description": f"👀 {title}\n\n✨ {tag_str}",
                "tags": tags[:8] if tags else ["视频", "干货", "分享"]
            },
            "channels": {
                "title": title[:20],
                "description": f"分享视频 {tag_str}",
                "tags": tags[:5] if tags else ["视频"]
            },
            "kuaishou": {
                "title": title[:15],
                "description": f"老铁们好 {tag_str}",
                "tags": tags[:5] if tags else ["视频"]
            }
        }

    def _generate_html_report(self, video_info, content):
        """生成HTML发布包"""
        today = datetime.now().strftime("%Y-%m-%d")

        platforms_html = ""
        platforms = [
            ("douyin", "抖音", "📱"),
            ("bilibili", "B站", "🎬"),
            ("xiaohongshu", "小红书", "📕"),
            ("channels", "视频号", "📺"),
            ("kuaishou", "快手", "🎥")
        ]

        for key, name, emoji in platforms:
            if key in content:
                p = content[key]
                tags_str = " ".join([f"#{t}" if not t.startswith("#") else t for t in p.get("tags", [])])
                platforms_html += f'''
                <div class="platform-section">
                    <h3>{emoji} {name}</h3>
                    <div class="field">
                        <label>标题：</label>
                        <div class="content-box" onclick="copyText(this)">{p.get("title", "")}</div>
                    </div>
                    <div class="field">
                        <label>描述：</label>
                        <div class="content-box textarea" onclick="copyText(this)">{p.get("description", "")}</div>
                    </div>
                    <div class="field">
                        <label>话题：</label>
                        <div class="content-box tags" onclick="copyText(this)">{tags_str}</div>
                    </div>
                </div>'''

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>多平台发布包 - {today}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #e91e63 0%, #9c27b0 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .video-info {{ background: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .video-info h2 {{ margin: 0 0 10px 0; font-size: 18px; color: #333; }}
        .video-info p {{ margin: 5px 0; color: #666; font-size: 14px; }}
        .platform-section {{ background: white; padding: 20px; border-radius: 12px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .platform-section h3 {{ margin: 0 0 15px 0; font-size: 16px; color: #333; border-bottom: 2px solid #e91e63; padding-bottom: 8px; }}
        .field {{ margin-bottom: 12px; }}
        .field label {{ display: block; font-weight: 600; color: #555; margin-bottom: 5px; font-size: 13px; }}
        .content-box {{ background: #f8f9fa; padding: 12px; border-radius: 6px; cursor: pointer; transition: background 0.2s; font-size: 14px; line-height: 1.5; word-break: break-all; }}
        .content-box:hover {{ background: #e3f2fd; }}
        .content-box.textarea {{ min-height: 60px; white-space: pre-wrap; }}
        .content-box.tags {{ color: #1976d2; }}
        .copied {{ background: #c8e6c9 !important; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
        .copy-hint {{ background: #fff3cd; padding: 10px; border-radius: 6px; margin-bottom: 15px; font-size: 13px; color: #856404; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📤 多平台视频发布包</h1>
        <p>{today}</p>
    </div>

    <div class="video-info">
        <h2>📹 {video_info.get("title", "未命名")}</h2>
        <p>{video_info.get("description", "无描述")}</p>
        <p>类型: {video_info.get("type", "通用")} | 时长: {video_info.get("duration", "未知")}</p>
    </div>

    <div class="copy-hint">💡 点击任意内容即可复制</div>

    {platforms_html}

    <div class="footer">
        由多平台发布秘书自动生成 | 建议配合各平台创作者中心使用
    </div>

    <script>
        function copyText(element) {{
            const text = element.textContent.trim();
            navigator.clipboard.writeText(text).then(() => {{
                element.classList.add('copied');
                setTimeout(() => element.classList.remove('copied'), 500);
            }});
        }}
    </script>
</body>
</html>'''

        return html

    def save_package(self, video_info, content):
        """保存发布包"""
        output_folder = self.config.get("output_folder",
            os.path.join(os.path.dirname(__file__), "output"))
        os.makedirs(output_folder, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")

        # 保存HTML
        html_content = self._generate_html_report(video_info, content)
        html_path = os.path.join(output_folder, f"publish_package_{today}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # 保存JSON备份
        json_path = os.path.join(output_folder, f"publish_package_{today}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "date": today,
                "video_info": video_info,
                "content": content
            }, f, ensure_ascii=False, indent=2)

        print(f"发布包已保存到: {html_path}")
        return html_path

    def run(self, title="", description="", tags=None, video_type="通用", duration=""):
        """运行生成"""
        if not title:
            print("错误：请提供视频标题")
            print("用法: python publish-agent/server.py --title '标题' --description '描述' --tags '标签1' '标签2'")
            return 1

        video_info = {
            "title": title,
            "description": description,
            "tags": tags or [],
            "type": video_type,
            "duration": duration
        }

        print("📝 正在生成各平台适配内容...")
        content = self.generate_content(video_info)

        if content:
            print("✅ 内容生成成功！")
            self.save_package(video_info, content)
            return 0
        else:
            print("❌ 内容生成失败，请检查配置")
            return 1


def main():
    parser = argparse.ArgumentParser(description="多平台发布秘书")
    parser.add_argument("--title", "-t", required=True, help="视频标题")
    parser.add_argument("--description", "-d", default="", help="视频简介")
    parser.add_argument("--tags", nargs="*", help="话题标签")
    parser.add_argument("--type", default="通用", choices=["知识科普", "日常vlog", "产品测评", "教程", "其他"],
                        help="视频类型")
    parser.add_argument("--duration", default="", help="视频时长")

    args = parser.parse_args()

    agent = PublishAgent()
    return agent.run(
        title=args.title,
        description=args.description,
        tags=args.tags,
        video_type=args.type,
        duration=args.duration
    )


if __name__ == "__main__":
    sys.exit(main())
