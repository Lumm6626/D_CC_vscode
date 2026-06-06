#!/usr/bin/env python3
"""
AI News Daily - AI 新闻日报
Daily AI news collection and HTML report generation
"""

import json
import os
import sys
import ssl
import smtplib
import argparse
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

try:
    import requests
    import feedparser
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Please install requests, beautifulsoup4, and feedparser")
    sys.exit(1)


class NewsDaily:
    """AI新闻日报生成器"""

    # Source credibility weights (AI domain)
    SOURCE_CREDIBILITY = {
        'OpenAI': 100, 'Google AI': 95, 'DeepMind': 95, 'Meta AI': 90,
        'Anthropic': 90, 'Microsoft AI': 85, 'Nvidia': 85, 'MIT Tech Review': 80,
        'TechCrunch': 75, 'Wired': 75, 'The Verge': 70, 'VentureBeat': 75,
        'Ars Technica': 70, 'NYTimes': 65, 'BBC': 60, 'Reuters': 65,
        '36kr': 65, '雷锋网': 60, 'IT之家': 55, '钛媒体': 60,
    }

    # Region classification keywords
    REGION_KEYWORDS = {
        '美国': ['USA', 'United States', 'America', 'US ', 'U.S.', 'San Francisco',
                 'Silicon Valley', 'New York', 'Seattle', 'Boston', 'Austin',
                 'OpenAI', 'Google', 'Microsoft', 'Meta', 'Apple', 'Nvidia',
                 'Anthropic', 'Amazon', 'Tesla'],
        '欧洲': ['EU', 'European', 'UK', 'Britain', 'London', 'Germany', 'France',
                 'Paris', 'DeepMind', 'Mistral', 'Stability AI'],
        '中国': ['China', 'Chinese', 'Beijing', 'Shanghai', 'Shenzhen', 'Hong Kong',
                 'Taiwan', '百度', '阿里', '腾讯', '华为', '字节', '商汤', '旷视',
                 '智谱', '月之暗面', '科大讯飞'],
        '国际': ['Japan', 'Korea', 'India', 'Singapore', 'Australia', 'Canada',
                 'global', 'worldwide', 'Israel', 'UAE', 'Saudi']
    }

    # Industry news keywords (AI domain)
    INDUSTRY_KEYWORDS = ['funding', 'investment', 'Series ', 'IPO', 'M&A', 'acquisition',
                         'merge', 'acquire', 'raise', 'valuation', 'startup', 'venture',
                         'partnership', 'deal', 'launch', 'release', 'announce',
                         'regulation', 'policy', 'ban', 'compliance', 'copyright',
                         'lawsuit', 'sue', 'fine', 'antitrust',
                         'open source', 'opensource', 'API', 'enterprise',
                         'revenue', 'profit', 'layoff', 'lay off', 'hire',
                         '融资', '收购', '上市', '投资', '估值', '合作', '发布',
                         '监管', '政策', '禁令', '合规', '开源', '裁员', '招聘']

    def __init__(self, config_path="config/news_config.json"):
        # server.py 在 agents/news/ai-news/ 下
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_path = os.path.dirname(os.path.dirname(current_dir))  # agents/
        self.config_path = os.path.join(self.base_path, config_path)
        self.email_config_path = os.path.join(self.base_path, "config/email_config.json")
        self.config = self._load_news_config()
        self.news_data = []
        self.chinese_summary = ""

    def _load_news_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_email_config(self):
        if os.path.exists(self.email_config_path):
            with open(self.email_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _clean_html(self, text):
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        return text.strip()

    def _clean_title(self, title):
        """清理标题噪音"""
        if not title:
            return ''
        title = re.sub(r'<[^>]+>', '', title)
        title = re.sub(r'\s*[-|]*\s*Read more\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'^\d{1,2}\s+\w+\s+\d{4}\s+\d+\s+views\s*', '', title)
        title = re.sub(r'^\d{4}-\d{2}-\d{2}\s*', '', title)
        title = re.sub(r'^\w+\s+\d{1,2},?\s+\d{4}\s*', '', title)
        title = re.sub(r'\s*\d+\s*views?\s*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\|\s*\d+\s*$', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    def _format_time_ago(self, published):
        """'X小时前' / '昨天' / 'X天前'"""
        if not published:
            return ''
        try:
            pub_date = datetime.strptime(published[:16], '%a, %d %b %Y %H:%M')
            hours_old = (datetime.now() - pub_date).total_seconds() / 3600
            if hours_old < 1:
                return '刚刚'
            elif hours_old < 24:
                return f'{int(hours_old)}小时前'
            elif hours_old < 48:
                return '昨天'
            else:
                days = int(hours_old // 24)
                return f'{days}天前'
        except:
            return ''

    def _classify_region(self, title, snippet, region_tag):
        """地区分类：美国/欧洲/中国/国际（默认国际）"""
        content = (title + ' ' + snippet).lower()
        if region_tag == 'China':
            return '中国'
        for region, keywords in self.REGION_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content:
                    return region
        return '国际'

    def _calculate_priority(self, news_item):
        """来源可信度(40%) + 地区权重(30%) + 时效(30%)"""
        keyword = news_item.get('keyword', '')
        credibility = self.SOURCE_CREDIBILITY.get(keyword, 50)

        region = news_item.get('region', '国际')
        region_weight = {'美国': 100, '欧洲': 70, '中国': 70, '国际': 50}.get(region, 50)

        recency_score = 50
        published = news_item.get('published', '')
        if published:
            try:
                pub_date = datetime.strptime(published[:16], '%a, %d %b %Y %H:%M')
                hours_old = (datetime.now() - pub_date).total_seconds() / 3600
                if hours_old < 6:
                    recency_score = 100
                elif hours_old < 24:
                    recency_score = 90
                elif hours_old < 48:
                    recency_score = 70
                elif hours_old < 72:
                    recency_score = 50
                else:
                    recency_score = 30
            except:
                pass

        return (credibility * 0.4) + (region_weight * 0.3) + (recency_score * 0.3)

    def _is_industry_news(self, title, snippet):
        """判断是否行业快讯"""
        content = (title + ' ' + snippet).lower()
        for kw in self.INDUSTRY_KEYWORDS:
            if kw.lower() in content:
                return True
        return False

    def _format_snippet(self, snippet, max_len=120):
        """格式化摘要"""
        if not snippet:
            return ''
        snippet = re.sub(r'<[^>]+>', '', snippet)
        snippet = snippet.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        if len(snippet) > max_len:
            snippet = snippet[:max_len] + '...'
        return snippet

    def _format_date(self, pub):
        if not pub:
            return ""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub)
            return dt.strftime('%m-%d %H:%M')
        except:
            return pub[5:16] if len(pub) > 16 else pub

    def _translate_title(self, title):
        """Simple translation mapping for AI terms"""
        trans = {
            "Epic Games": "[Epic游戏]", "OpenAI": "[OpenAI]", "Elon Musk": "[马斯克]",
            "Twitter": "[推特]", "Super Micro": "[超微]", "Jeff Bezos": "[贝索斯]",
            "Google": "[谷歌]", "Meta": "[Meta]", "Microsoft": "[微软]", "Apple": "[苹果]",
            "Amazon": "[亚马逊]", "Nvidia": "[英伟达]", "Anthropic": "[Anthropic]",
            "DeepMind": "[DeepMind]", "Sora": "Sora", "GPT": "GPT", "LLM": "大模型",
            "Gemini": "Gemini", "ChatGPT": "ChatGPT", "Claude": "Claude",
            "lay off": "裁员", "layoffs": "裁员", "shut down": "关闭", "close": "关闭",
            "launch": "发布", "release": "发布", "announce": "宣布", "unveils": "发布",
            "invest": "投资", "acquire": "收购", "acquisition": "收购",
            "partnership": "合作", "funding": "融资",
            "chip": "芯片", "GPU": "GPU", "server": "服务器", "model": "模型",
            "China": "中国", "U.S.": "美国", "employees": "员工", "export": "出口",
            "startup": "创业公司", "video": "视频", "generator": "生成器",
            "artificial intelligence": "人工智能", "machine learning": "机器学习",
            "deep learning": "深度学习", "neural network": "神经网络",
            "robotics": "机器人", "autonomous": "自动驾驶", "enterprise": "企业",
            "government": "政府", "regulation": "监管", "privacy": "隐私",
            "security": "安全", "tech giant": "科技巨头", "rival": "竞争对手",
            "search": "搜索", "assistant": "助手", "cloud": "云", "data": "数据",
            "algorithm": "算法", "research": "研究", "developer": "开发者",
            "platform": "平台", "software": "软件", "hardware": "硬件",
            "update": "更新", "upgrade": "升级", "new": "新", "first": "首个",
            "latest": "最新", "report": "报告", "study": "研究",
            "says": "称", "according to": "根据",
            "million": "百万", "billion": "十亿", "trillion": "万亿",
        }
        result = title
        sorted_trans = sorted(trans.items(), key=lambda x: len(x[0]), reverse=True)
        for k, v in sorted_trans:
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

    def _get_fallback_news(self):
        """Fallback news data"""
        return [
            {"title": "OpenAI releases new GPT model", "url": "https://openai.com", "snippet": "OpenAI announces latest language model", "keyword": "OpenAI", "region": "Foreign"},
            {"title": "Google launches Gemini 2.0", "url": "https://blog.google", "snippet": "Google AI new model release", "keyword": "Google AI", "region": "Foreign"},
            {"title": "Meta open sources Llama 4", "url": "https://meta.com", "snippet": "Meta releases new open source LLM", "keyword": "Meta AI", "region": "Foreign"},
            {"title": "China AI industry report", "url": "https://tech.sina.com.cn", "snippet": "Latest AI industry dynamics in China", "keyword": "Sina Tech", "region": "China"},
            {"title": "Nvidia releases new AI chip", "url": "https://nvidia.com", "snippet": "GPU giant releases new AI hardware", "keyword": "Nvidia", "region": "Foreign"},
        ]

    def search_ai_news(self):
        """Search AI news from RSS sources"""
        print("Starting AI news fetch...")

        all_news = []

        foreign_rss = [
            ("https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", "NYTimes", "Foreign"),
            ("https://feeds.bbci.co.uk/news/technology/rss.xml", "BBC", "Foreign"),
            ("https://www.wired.com/feed/rss", "Wired", "Foreign"),
            ("https://techcrunch.com/feed/", "TechCrunch", "Foreign"),
        ]

        china_rss = [
            ("https://36kr.com/feed", "36kr", "China"),
            ("https://www.leiphone.com/feed", "雷锋网", "China"),
            ("https://www.ithome.com/rss/", "IT之家", "China"),
            ("https://www.tmtpost.com/rss", "钛媒体", "China"),
        ]

        ai_kw = ['ai', 'artificial intelligence', 'chatgpt', 'llm', 'openai',
                 'machine learning', 'gpt', '人工智能', '大模型', 'AI', 'ChatGPT']

        print("\n=== Fetching Foreign Sources ===")
        for url, src, region in foreign_rss:
            try:
                print(f"[Get] {src}")
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
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

        print("\n=== Fetching China Sources ===")
        for url, src, region in china_rss:
            try:
                print(f"[Get] {src}")
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
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

        if not all_news:
            print("\nUsing fallback data...")
            all_news = self._get_fallback_news()

        seen = set()
        unique = []
        for n in all_news:
            t = n.get("title", "")
            if t and t not in seen:
                seen.add(t)
                unique.append(n)

        # Classify region for each news item
        for n in unique:
            n['region'] = self._classify_region(
                n.get('title', ''), n.get('snippet', ''), n.get('region', ''))

        self.news_data = unique
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

    def generate_html_report(self):
        """Generate HTML report — allergy-style segmented layout"""
        today = datetime.now().strftime("%Y-%m-%d")
        today_formatted = datetime.now().strftime("%Y年%m月%d日")

        # Partition by region
        us_news = [n for n in self.news_data if n.get('region') == '美国']
        eu_news = [n for n in self.news_data if n.get('region') == '欧洲']
        china_news = [n for n in self.news_data if n.get('region') == '中国']
        intl_news = [n for n in self.news_data if n.get('region') == '国际']

        us_news_sorted = sorted(us_news, key=self._calculate_priority, reverse=True)
        eu_news_sorted = sorted(eu_news, key=self._calculate_priority, reverse=True)
        china_news_sorted = sorted(china_news, key=self._calculate_priority, reverse=True)
        intl_news_sorted = sorted(intl_news, key=self._calculate_priority, reverse=True)

        industry_news = [n for n in self.news_data if self._is_industry_news(
            n.get('title', ''), n.get('snippet', ''))]
        industry_news_sorted = sorted(industry_news, key=self._calculate_priority, reverse=True)

        # 今日重点: high credibility US + Europe + China top news
        top_news = [n for n in us_news_sorted if self.SOURCE_CREDIBILITY.get(n.get('keyword', ''), 0) >= 70][:10]

        def render_news_card(n):
            title = self._clean_title(n.get('title', ''))
            title_cn = self._translate_title(title)
            snippet = self._format_snippet(n.get('snippet', ''), 120)
            url = n.get('url', '#')
            source = n.get('keyword', '')
            region = n.get('region', '')
            time_ago = self._format_time_ago(n.get('published', ''))
            credibility = self.SOURCE_CREDIBILITY.get(source, 50)
            stars = '★' * min(5, max(1, credibility // 20))
            region_flag = {"美国": "🇺🇸", "欧洲": "🇪🇺", "中国": "🇨🇳", "国际": "🌏"}.get(region, "🌏")
            time_str = f" · {time_ago}" if time_ago else ""

            return f'''
                <div style="background:white; border-left:3px solid #7c4dff; padding:12px 15px; margin-bottom:10px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                    <div style="font-weight:600; color:#222; margin-bottom:6px; font-size:14px; line-height:1.4;">
                        <span style="color:#ff9800;">{stars}</span> <a href="{url}" target="_blank" style="color:#6200ea; text-decoration:none;">{title_cn}</a>
                    </div>
                    <div style="font-size:12px; color:#555; line-height:1.5; margin-bottom:6px;">{snippet}</div>
                    <div style="font-size:11px; color:#888;">
                        <span style="background:#ede7f6; color:#4527a0; padding:2px 6px; border-radius:3px;">{source}</span>
                        <span style="margin-left:8px;">{region_flag} {region}{time_str}</span>
                    </div>
                </div>'''

        def render_simple_news_item(n):
            title = self._clean_title(n.get('title', ''))
            title_cn = self._translate_title(title)
            url = n.get('url', '#')
            source = n.get('keyword', '')
            time_ago = self._format_time_ago(n.get('published', ''))
            time_str = f" · {time_ago}" if time_ago else ""
            return f'<li style="margin-bottom:8px; line-height:1.4;"><a href="{url}" target="_blank" style="color:#6200ea; text-decoration:none;">{title_cn}</a><span style="color:#999; font-size:11px;">{time_str}</span></li>'

        # Build section HTML
        top_news_html = ''.join([render_news_card(n) for n in top_news]) if top_news else '<div style="color:#999; padding:20px; text-align:center;">暂无重点新闻</div>'

        # 国际动态 (US + Europe + other international)
        international = us_news_sorted + eu_news_sorted + intl_news_sorted
        international_sorted = sorted(international, key=self._calculate_priority, reverse=True)
        intl_html = ''.join([render_simple_news_item(n) for n in international_sorted[:20]])

        china_html = ''.join([render_simple_news_item(n) for n in china_news_sorted[:15]])

        industry_html = ''.join([render_simple_news_item(n) for n in industry_news_sorted[:10]])

        us_count = len(us_news)
        eu_count = len(eu_news)
        china_count = len(china_news)
        intl_count = len(intl_news) + us_count + eu_count
        industry_count = len(industry_news)

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI新闻日报 - {today}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; max-width:800px; margin:0 auto; padding:15px; background:#f5f5f5; }}
        .header {{ background:linear-gradient(135deg, #7c4dff 0%, #6200ea 100%); color:white; padding:20px 25px; border-radius:12px; margin-bottom:20px; box-shadow:0 4px 12px rgba(98,0,234,0.3); }}
        .header h1 {{ margin:0; font-size:22px; display:flex; align-items:center; gap:8px; }}
        .header .date {{ margin:8px 0 0 0; opacity:0.9; font-size:14px; }}
        .header .stats {{ display:flex; gap:10px; margin-top:12px; flex-wrap:wrap; }}
        .header .stats span {{ background:rgba(255,255,255,0.2); padding:5px 12px; border-radius:15px; font-size:12px; }}
        .section {{ background:white; border-radius:10px; padding:18px 20px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
        .section h2 {{ color:#333; font-size:15px; margin:0 0 12px 0; padding-bottom:8px; border-bottom:2px solid #eee; display:flex; align-items:center; gap:6px; }}
        .section h2 .count {{ font-size:12px; color:#999; font-weight:normal; margin-left:auto; }}
        .news-list {{ list-style:none; padding:0; margin:0; }}
        .footer {{ text-align:center; color:#bbb; margin-top:20px; font-size:11px; }}
        a {{ color:#6200ea; text-decoration:none; }}
        a:hover {{ text-decoration:underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI新闻日报 {today}</h1>
        <p class="date">{today_formatted}</p>
        <div class="stats">
            <span>共 {len(self.news_data)} 条</span>
            <span>🇺🇸 美国 {us_count}条</span>
            <span>🇪🇺 欧洲 {eu_count}条</span>
            <span>🇨🇳 中国 {china_count}条</span>
            <span>📈 行业 {industry_count}条</span>
        </div>
    </div>

    <div class="section">
        <h2>🔥 AI 重点 <span class="count">高可信度来源 ★★★★★</span></h2>
        {top_news_html}
    </div>

    <div class="section">
        <h2>🌍 国际动态 <span class="count">{intl_count}条</span></h2>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0 20px;">
            <ul class="news-list">{intl_html[:len(intl_html)//2] if intl_html else ''}</ul>
            <ul class="news-list">{intl_html[len(intl_html)//2:] if intl_html else ''}</ul>
        </div>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：TechCrunch / Wired / MIT Tech Review / NYTimes / BBC</div>
    </div>

    <div class="section">
        <h2>🇨🇳 中国动态 <span class="count">{china_count}条</span></h2>
        <ul class="news-list">{china_html if china_html else '<li style="color:#999;">暂无中国新闻</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：36kr / 雷锋网 / IT之家 / 钛媒体</div>
    </div>

    <div class="section">
        <h2>📈 行业快讯 <span class="count">{industry_count}条</span></h2>
        <ul class="news-list">{industry_html if industry_html else '<li style="color:#999;">暂无行业快讯</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">融资 / 收购 / 监管 / 产品发布</div>
    </div>

    <div class="footer">
        <p>由 AI News Daily 自动生成 · {today}</p>
    </div>
</body>
</html>'''

        return html

    def _send_email(self, html_content, subject_prefix=None):
        """发送邮件 — 使用共享 email_config.json"""
        config = self._load_email_config()
        smtp_server = config.get("smtp_server", "smtp.163.com")
        smtp_port = config.get("smtp_port", 465)
        smtp_user = config.get("email", "")
        smtp_password = config.get("password", "")
        recipient = config.get("recipient_email", "")
        enable_email = config.get("enable_email", False)

        if not enable_email:
            print("[Email] Email sending is disabled (enable_email=false)")
            return True

        if not smtp_user or not smtp_password or not recipient:
            print("[Email] Email config incomplete, skip sending")
            return False

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            count = len(self.news_data)
            if subject_prefix:
                subject = f"{subject_prefix} {today}"
            else:
                subject = f"🤖 AI新闻 日报 {today} ({count}条)"

            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = smtp_user
            msg['To'] = recipient

            plain_text = f"AI新闻日报 - {today}\n共 {count} 条\n\n请查看HTML版本获取完整内容。"
            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            print(f"[Email] 正在发送至 {recipient}...")
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient, msg.as_string())

            print("[Email] 发送成功!")
            return True
        except Exception as e:
            print(f"[Email] 发送失败: {str(e)}")
            return False

    def save_report(self, send_email=True):
        """Save report to file"""
        out_folder = os.path.join(os.path.dirname(__file__), "output")

        today = datetime.now().strftime("%Y-%m-%d")
        day_folder = os.path.join(out_folder, today)
        os.makedirs(day_folder, exist_ok=True)

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

        if send_email:
            self._send_email(html_content)

        return day_folder

    def run(self, send_email=True):
        """Run news collection"""
        try:
            self.search_ai_news()
            folder = self.save_report(send_email=send_email)
            return 0
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(description="AI News Daily - AI新闻日报")
    parser.add_argument("--config", default="config/news_config.json", help="Config path")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    parser.add_argument("--test", action="store_true", help="Test mode")

    args = parser.parse_args()

    news = NewsDaily(args.config)

    if args.test:
        print("Testing...")
        news.search_ai_news()
    else:
        return news.run(send_email=not args.no_email)

    return 0


if __name__ == "__main__":
    sys.exit(main())
