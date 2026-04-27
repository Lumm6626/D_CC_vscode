#!/usr/bin/env python3
"""
News Daily - AI News Reporter
Daily AI news collection and HTML report generation
"""

import json
import os
import sys
import argparse
from datetime import datetime
from urllib.parse import quote_plus
import re

try:
    import requests
    from bs4 import BeautifulSoup
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.header import Header
except ImportError:
    print("Error: Please install requests and beautifulsoup4")
    sys.exit(1)


class NewsDaily:
    def __init__(self, config_path="config/news_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.news_data = []
        self.summary = ""

    def _load_config(self):
        """Load config file"""
        config_file = os.path.join(os.path.dirname(__file__), "..", self.config_path)
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _clean_html(self, text):
        """Clean HTML tags"""
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        return text.strip()

    def _get_fallback_news(self):
        """Fallback news data"""
        return [
            {"title": "OpenAI releases new GPT model", "url": "https://openai.com", "snippet": "OpenAI announces latest language model", "keyword": "OpenAI", "region": "Foreign"},
            {"title": "Google launches Gemini 2.0", "url": "https://blog.google", "snippet": "Google AI new model release", "keyword": "Google AI", "region": "Foreign"},
            {"title": "Meta open sources Llama 4", "url": "https://meta.com", "snippet": "Meta releases new open source LLM", "keyword": "Meta AI", "region": "Foreign"},
            {"title": "China AI industry report", "url": "https://tech.sina.com.cn", "snippet": "Latest AI industry dynamics in China", "keyword": "Sina Tech", "region": "China"},
            {"title": "Nvidia releases new AI chip", "url": "https://nvidia.com", "snippet": "GPU giant releases new AI hardware", "keyword": "Nvidia", "region": "Foreign"},
        ]

    def _translate_title(self, title):
        """Simple translation mapping"""
        trans = {
            "Epic Games": "[Epic游戏]",
            "OpenAI": "[OpenAI]",
            "Elon Musk": "[马斯克]",
            "Twitter": "[推特]",
            "Super Micro": "[超微]",
            "Jeff Bezos": "[贝索斯]",
            "Google": "[谷歌]",
            "Meta": "[Meta]",
            "Microsoft": "[微软]",
            "Apple": "[苹果]",
            "Amazon": "[亚马逊]",
            "Nvidia": "[英伟达]",
            "AI": "AI",
            "Sora": "Sora",
            "GPT": "GPT",
            "LLM": "大模型",
            "Gemini": "Gemini",
            "ChatGPT": "ChatGPT",
            "lay off": "裁员",
            "layoffs": "裁员",
            "shut down": "关闭",
            "close": "关闭",
            "launch": "发布",
            "release": "发布",
            "announce": "宣布",
            "unveils": "发布",
            "invest": "投资",
            "acquire": "收购",
            "acquisition": "收购",
            "partnership": "合作",
            "funding": "融资",
            "chip": "芯片",
            "GPU": "GPU",
            "server": "服务器",
            "model": "模型",
            "China": "中国",
            "U.S.": "美国",
            "employees": "员工",
            "shareholder": "股东",
            "export": "出口",
            "laws": "法律",
            "indicted": "被起诉",
            "startup": "创业公司",
            "video": "视频",
            "generator": "生成器",
            "artificial intelligence": "人工智能",
            "machine learning": "机器学习",
            "deep learning": "深度学习",
            "neural network": "神经网络",
            "robotics": "机器人",
            "autonomous": "自动驾驶",
            "enterprise": "企业",
            "government": "政府",
            "regulation": "监管",
            "privacy": "隐私",
            "security": "安全",
            "tech giant": "科技巨头",
            "rival": "竞争对手",
            "search": "搜索",
            "assistant": "助手",
            "cloud": "云",
            "data": "数据",
            "algorithm": "算法",
            "research": "研究",
            "developer": "开发者",
            "platform": "平台",
            "software": "软件",
            "hardware": "硬件",
            "system": "系统",
            "update": "更新",
            "upgrade": "升级",
            "new": "新",
            "first": "首个",
            "latest": "最新",
            "report": "报告",
            "study": "研究",
            "says": "称",
            "according to": "根据",
            "million": "百万",
            "billion": "十亿",
        }
        result = title
        for k, v in trans.items():
            result = result.replace(k, v)
        result = result.replace(", ", " ").replace(".", "").replace("  ", " ")
        return result.strip()

    def _translate_to_chinese(self, text):
        """使用MyMemory免费API翻译文本为中文"""
        try:
            import urllib.request
            import urllib.parse
            url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text[:500])}&langpair=en|zh-CN"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('responseStatus') == 200:
                    return result['responseData']['translatedText']
        except Exception as e:
            print(f"[翻译] 翻译失败: {str(e)[:50]}")
        return None

    def search_ai_news(self):
        """Search AI news from RSS sources"""
        print("Starting AI news fetch...")

        all_news = []

        # Foreign RSS sources
        foreign_rss = [
            ("https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", "NYTimes", "Foreign"),
            ("https://feeds.bbci.co.uk/news/technology/rss.xml", "BBC", "Foreign"),
            ("https://www.wired.com/feed/rss", "Wired", "Foreign"),
            ("https://techcrunch.com/feed/", "TechCrunch", "Foreign"),
        ]

        # China RSS sources
        china_rss = [
            ("https://36kr.com/feed", "36kr", "China"),
            ("https://www.leiphone.com/feed", "雷锋网", "China"),
            ("https://www.ithome.com/rss/", "IT之家", "China"),
            ("https://www.tmtpost.com/rss", "钛媒体", "China"),
        ]

        # AI keywords
        ai_kw = ['ai', 'artificial intelligence', 'chatgpt', 'llm', 'openai', 'machine learning', 'gpt', '人工智能', '大模型', 'AI', 'ChatGPT']

        # Fetch foreign
        print("\n=== Fetching Foreign Sources ===")
        for url, src, region in foreign_rss:
            try:
                print(f"[Get] {src}")
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    import feedparser
                    feed = feedparser.parse(resp.text)
                    for ent in feed.entries[:15]:
                        title = ent.get('title', '')
                        summary = ent.get('summary', '') or ent.get('description', '')
                        content = (title + ' ' + summary).lower()
                        if any(k in content for k in ai_kw):
                            pub = ""
                            if hasattr(ent, 'published'):
                                pub = ent.published
                            all_news.append({
                                "title": title,
                                "url": ent.get('link', ''),
                                "snippet": self._clean_html(summary[:200]) if summary else '',
                                "keyword": src,
                                "region": region,
                                "published": pub
                            })
            except Exception as e:
                print(f"  Error: {str(e)[:40]}")

        # Fetch China
        print("\n=== Fetching China Sources ===")
        for url, src, region in china_rss:
            try:
                print(f"[Get] {src}")
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    import feedparser
                    feed = feedparser.parse(resp.content.decode('utf-8', errors='ignore'))
                    for ent in feed.entries[:10]:
                        title = ent.get('title', '')
                        summary = ent.get('summary', '') or ent.get('description', '')
                        content = (title + ' ' + summary).lower()
                        if any(k in content for k in ai_kw):
                            pub = ""
                            if hasattr(ent, 'published'):
                                pub = ent.published
                            all_news.append({
                                "title": title,
                                "url": ent.get('link', ''),
                                "snippet": self._clean_html(summary[:200]) if summary else '',
                                "keyword": src,
                                "region": region,
                                "published": pub
                            })
            except Exception as e:
                print(f"  Error: {str(e)[:40]}")

        # Fallback
        if not all_news:
            print("\nUsing fallback data...")
            all_news = self._get_fallback_news()

        # Deduplicate
        seen = set()
        unique = []
        for n in all_news:
            t = n.get("title", "")
            if t and t not in seen:
                seen.add(t)
                unique.append(n)

        self.news_data = unique
        self._generate_summary()
        print(f"\n[Total] {len(unique)} news fetched")
        return unique

    def _categorize_news(self):
        """Categorize news by topic"""
        cats = {
            "LLM/Model": ["GPT", "LLM", "Gemini", "Llama", "Claude", "Model", "大模型"],
            "AI Product": ["ChatGPT", "OpenAI", "Google", "Meta", "Apple", "Microsoft", "AI", "Product"],
            "AI Video": ["Sora", "Video", "DALL-E", "Image"],
            "AI Chip": ["Chip", "Nvidia", "GPU", "Hardware", "芯片", "硬件"],
            "AI Industry": ["Company", "Funding", "Acquire", "Partner", "Industry", "行业"]
        }

        result = {k: [] for k in cats}
        result["Other"] = []

        for news in self.news_data:
            title = news.get("title", "")
            matched = False
            for cat, kws in cats.items():
                if any(k.lower() in title.lower() for k in kws):
                    result[cat].append(news)
                    matched = True
                    break
            if not matched:
                result["Other"].append(news)

        return {k: v for k, v in result.items() if v}

    def _format_date(self, pub):
        """Format date"""
        if not pub:
            return ""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub)
            return dt.strftime('%m-%d %H:%M')
        except:
            return pub[5:16] if len(pub) > 16 else pub

    def _generate_summary(self):
        """Generate summary with Chinese highlights"""
        cats = self._categorize_news()
        cat_counts = {k: len(v) for k, v in cats.items()}
        sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)

        # Build category tags
        cat_html = ""
        for cat, cnt in sorted_cats:
            icon = {"LLM/Model": "LLM", "AI Product": "AI", "AI Video": "VID", "AI Chip": "HW", "AI Industry": "Biz"}.get(cat, "News")
            cat_html += f'<span class="cat-tag">{icon} {cat} ({cnt})</span>'

        # 生成中文要点摘要
        chinese_highlights = self._get_chinese_highlights()

        self.summary = f'''
    <div class="summary-section">
        <h2>AI Daily Highlights</h2>
        <div class="category-tags">{cat_html}</div>

        <div class="chinese-summary">
            <h3>Top 10 AI News</h3>
            {chinese_highlights}
        </div>
    </div>'''

        # 中文摘要放在最头部
        self.chinese_summary = self._build_chinese_top10()

    def _build_chinese_top10(self):
        """根据当日新闻生成Top10重要内容中文摘要"""
        # 这里是需要AI分析才能生成的摘要内容
        # 目前返回占位符，实际使用时由save_report调用时传入
        return ""

    def _get_chinese_highlights(self):
        """Get Chinese highlights - 使用翻译API将英文标题翻译为中文"""
        highlights = ""

        # 从news_data中取前10条，翻译标题
        for i, news in enumerate(self.news_data[:10], 1):
            title = news.get("title", "")
            snippet = news.get("snippet", "")[:200]
            url = news.get("url", "")
            pub = self._format_date(news.get("published", ""))
            src = news.get("keyword", "")
            region = news.get("region", "Foreign")

            # 翻译标题
            chinese_title = self._translate_to_chinese(title)
            if not chinese_title:
                chinese_title = self._translate_title(title)

            # 翻译摘要
            chinese_snippet = self._translate_to_chinese(snippet) if snippet else ""
            if not chinese_snippet:
                chinese_snippet = snippet[:100] + "..." if len(snippet) > 100 else snippet

            region_label = "🌍 全球" if region == "Foreign" else "🇨🇳 国内"

            highlights += f'''
            <div class="highlight-item">
                <span class="highlight-num">{i}</span>
                <div class="highlight-content">
                    <div class="highlight-title">
                        <a href="{url}" target="_blank" style="color: #333; text-decoration: none;">{chinese_title}</a>
                    </div>
                    <p class="highlight-snippet" style="color: #555; font-size: 13px; margin: 5px 0; line-height: 1.4;">{chinese_snippet}</p>
                    <div class="highlight-meta">
                        <span class="highlight-date">{pub}</span> |
                        <span class="highlight-source">{src}</span> |
                        <span style="color: #1976d2;">{region_label}</span>
                    </div>
                </div>
            </div>'''

        return highlights

    def _send_email(self, html_content, max_retries=3, retry_delay=5):
        """Send HTML report via email with retry mechanism"""
        smtp_server = self.config.get("smtp_server", "smtp.163.com")
        smtp_port = self.config.get("smtp_port", 465)
        smtp_user = self.config.get("smtp_user", "")
        smtp_password = self.config.get("smtp_password", "")
        recipient = self.config.get("recipient_email", "")
        enable_email = self.config.get("enable_email", False)

        if not enable_email:
            print("[Email] Email sending is disabled (enable_email=false)")
            return True

        if not smtp_user or not smtp_password or not recipient:
            print("[Email] Email config incomplete, skip sending")
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"AI News Daily - {today}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = smtp_user
        msg['To'] = recipient

        plain_text = f"AI News Daily - {today}\n\nPlease view the HTML version for full content."
        msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        for attempt in range(1, max_retries + 1):
            try:
                print(f"[Email] Attempt {attempt}/{max_retries} - Sending to {recipient}...")
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, recipient, msg.as_string())
                print(f"[Email] Sent successfully!")
                return True
            except Exception as e:
                print(f"[Email] Attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    print(f"[Email] Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                else:
                    print(f"[Email] All {max_retries} attempts failed")
        return False

    def generate_html_report(self, chinese_top10=""):
        """Generate HTML report"""
        today = datetime.now().strftime("%Y-%m-%d")

        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI News - {date}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .top10-section {{ background: white; padding: 25px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .top10-section h2 {{ margin: 0 0 15px 0; color: #1a1a1a; font-size: 20px; padding-bottom: 10px; border-bottom: 2px solid #ff6b6b; }}
        .top10-china {{ border-left: 4px solid #ff6b6b; }}
        .top10-china h2 {{ border-bottom-color: #ff6b6b; }}
        .top10-china .top10-item {{ background: #fff5f5; border-left-color: #ff6b6b; }}
        .top10-china .top10-num {{ background: #ff6b6b; }}
        .top10-global {{ border-left: 4px solid #1976d2; }}
        .top10-global h2 {{ border-bottom-color: #1976d2; }}
        .top10-global .top10-item {{ background: #f0f7ff; border-left-color: #1976d2; }}
        .top10-global .top10-num {{ background: #1976d2; }}
        .top10-list {{ display: flex; flex-direction: column; gap: 10px; }}
        .top10-item {{ display: flex; gap: 12px; padding: 12px; border-radius: 8px; }}
        .top10-num {{ color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; flex-shrink: 0; }}
        .top10-content {{ flex: 1; }}
        .top10-title {{ font-size: 14px; font-weight: 600; color: #333; line-height: 1.4; }}
        .top10-title a {{ color: #333; text-decoration: none; }}
        .top10-title a:hover {{ color: #667eea; }}
        .top10-desc {{ font-size: 13px; color: #666; line-height: 1.4; margin-top: 4px; }}
        .summary-section {{ background: white; padding: 25px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .summary-section h2 {{ margin: 0 0 20px 0; color: #1a1a1a; font-size: 20px; padding-bottom: 15px; border-bottom: 2px solid #667eea; }}
        .category-tags {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
        .cat-tag {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px; }}
        .highlight-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .highlight-item {{ display: flex; align-items: flex-start; gap: 12px; padding: 15px; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #667eea; }}
        .highlight-num {{ background: #667eea; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: bold; flex-shrink: 0; }}
        .highlight-content {{ flex: 1; }}
        .highlight-title {{ font-size: 16px; font-weight: 600; color: #333; line-height: 1.5; margin-bottom: 5px; }}
        .highlight-title a {{ color: #333; text-decoration: none; }}
        .highlight-title a:hover {{ color: #667eea; }}
        .highlight-snippet {{ font-size: 13px; color: #666; line-height: 1.5; margin: 5px 0; }}
        .highlight-meta {{ font-size: 13px; color: #888; }}
        .chinese-summary {{ margin-top: 20px; }}
        .chinese-summary h3 {{ color: #333; font-size: 18px; margin-bottom: 15px; }}
        .news-item {{ background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .news-date {{ color: #999; font-size: 12px; margin-bottom: 5px; }}
        .news-item h3 {{ margin: 0 0 10px 0; color: #333; }}
        .news-item a {{ color: #667eea; text-decoration: none; }}
        .snippet {{ color: #666; font-size: 14px; line-height: 1.6; }}
        .tag {{ display: inline-block; background: #e8f4f8; color: #2a7bb0; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 8px; }}
        .tag-china {{ background: #ffeaea; color: #d32f2f; }}
        .tag-foreign {{ background: #e3f2fd; color: #1976d2; }}
        .news-meta {{ margin-top: 10px; display: flex; align-items: center; flex-wrap: wrap; gap: 5px; }}
        .section-title {{ font-size: 16px; font-weight: bold; color: #333; margin: 20px 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #667eea; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI News Daily</h1>
        <p>{date} | {count} articles</p>
    </div>

    {chinese_top10}

    {summary}

    <div class="section-title">[All News]</div>
    {news_html}
    <div class="footer">
        Generated by AI News Assistant
    </div>
</body>
</html>"""

        news_html = ""
        for i, news in enumerate(self.news_data, 1):
            title = self._translate_title(news.get("title", ""))
            snippet = news.get("snippet", "")
            url = news.get("url", "")
            src = news.get("keyword", "")
            region = news.get("region", "Foreign")
            pub = self._format_date(news.get("published", ""))
            region_class = "tag-china" if region == "China" else "tag-foreign"
            region_icon = "CN" if region == "China" else "EN"

            news_html += f"""
    <div class="news-item">
        <div class="news-date">{pub}</div>
        <h3>{i}. {title}</h3>
        <p class="snippet">{snippet}</p>
        <div class="news-meta">
            <a href="{url}" target="_blank">Original</a>
            <span class="tag">{src}</span>
            <span class="tag {region_class}">{region_icon}</span>
        </div>
    </div>"""

        html_content = html_template.format(
            date=today,
            count=len(self.news_data),
            summary=self.summary,
            news_html=news_html,
            chinese_top10=self.chinese_summary if hasattr(self, 'chinese_summary') else ""
        )

        return html_content

    def save_report(self):
        """Save report to file"""
        out_folder = self.config.get("output_folder",
            os.path.join(os.path.dirname(__file__), "output"))

        today = datetime.now().strftime("%Y-%m-%d")
        day_folder = os.path.join(out_folder, today)
        os.makedirs(day_folder, exist_ok=True)

        # 生成中文Top10摘要
        self.chinese_summary = self._generate_chinese_top10_html()

        html_content = self.generate_html_report()

        html_path = os.path.join(day_folder, "ai_news.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        json_path = os.path.join(day_folder, "news.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "date": today,
                "count": len(self.news_data),
                "news": self.news_data
            }, f, ensure_ascii=False, indent=2)

        print(f"Report saved to: {day_folder}")

        # Send email
        self._send_email(html_content)

        return day_folder

    def _generate_top10_html(self, news_list, section_name, section_class):
        """根据新闻列表生成Top10重要内容的中文摘要HTML"""
        items_html = ""
        for i, news in enumerate(news_list[:10], 1):
            title = news.get("title", "")
            snippet = news.get("snippet", "")[:100]
            url = news.get("url", "")

            # 翻译标题和摘要
            chinese_title = self._translate_to_chinese(title)
            if not chinese_title:
                chinese_title = self._translate_title(title)

            chinese_snippet = self._translate_to_chinese(snippet) if snippet else ""
            if not chinese_snippet:
                chinese_snippet = snippet[:80]

            items_html += f'''
            <div class="top10-item">
                <span class="top10-num">{i}</span>
                <div class="top10-content">
                    <div class="top10-title"><a href="{url}" target="_blank">{chinese_title}</a></div>
                    <div class="top10-desc">{chinese_snippet}</div>
                </div>
            </div>'''

        return f'''
    <div class="top10-section {section_class}">
        <h2>{section_name}</h2>
        <div class="top10-list">{items_html}
        </div>
    </div>'''

    def _generate_chinese_top10_html(self):
        """分别生成中国和Global的Top10摘要"""
        china_news = [n for n in self.news_data if n.get("region") == "China"]
        global_news = [n for n in self.news_data if n.get("region") == "Foreign"]

        china_html = self._generate_top10_html(china_news, "🇨🇳 中国科技新闻 Top 10", "top10-china") if china_news else ""
        global_html = self._generate_top10_html(global_news, "🌍 全球科技新闻 Top 10", "top10-global") if global_news else ""

        return china_html + global_html

    def run(self):
        """Run news collection"""
        try:
            self.search_ai_news()
            folder = self.save_report()
            return 0
        except Exception as e:
            print(f"Error: {str(e)}")
            return 1


def main():
    parser = argparse.ArgumentParser(description="AI News Daily")
    parser.add_argument("--config", default="config/news_config.json", help="Config path")
    parser.add_argument("--test", action="store_true", help="Test")

    args = parser.parse_args()

    news = NewsDaily(args.config)

    if args.test:
        print("Testing...")
        news.search_ai_news()
    else:
        return news.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
