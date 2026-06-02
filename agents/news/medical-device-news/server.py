#!/usr/bin/env python3
"""
Medical Device News Daily
Daily medical device news collection and HTML report generation
"""

import json
import os
import sys
import argparse
from datetime import datetime
import re

try:
    import requests
    import feedparser
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.header import Header
except ImportError:
    print("Error: Please install requests")
    sys.exit(1)


DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


class MedicalDeviceNews:
    def __init__(self, config_path="config/medical_device_config.json"):
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
        if not text:
            return ""
        # 移除所有HTML标签
        text = re.sub(r'<[^>]*>', '', text)
        # 转换HTML实体
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&apos;', "'")
        # 清理多余空格
        text = ' '.join(text.split())
        return text.strip()

    def _clean_title(self, title):
        """Clean title - remove HTML tags and extra whitespace"""
        title = re.sub(r'<[^>]+>', '', title)
        title = title.replace('&nbsp;', ' ')
        title = title.replace('&amp;', '&')
        title = title.replace('&lt;', '<')
        title = title.replace('&gt;', '>')
        title = title.replace('&quot;', '"')
        title = ' '.join(title.split())
        return title.strip()

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

    def _translate_title(self, title):
        """Simple translation mapping for medical device terms"""
        trans = {
            "FDA": "美国FDA",
            "approval": "批准",
            "approved": "已批准",
            "clearance": "获批",
            "cleared": "已获批",
            "launch": "上市",
            "launches": "上市",
            "recall": "召回",
            "clinical trial": "临床试验",
            "study": "研究",
            "device": "器械",
            "implant": "植入物",
            "surgical": "外科",
            "robot": "机器人",
            "AI": "人工智能",
            "diagnostic": "诊断",
            "COVID-19": "新冠",
            "pandemic": "大流行",
            "healthcare": "医疗",
            "hospital": "医院",
            "patient": "患者",
            "treatment": "治疗",
            "therapy": "疗法",
            "device": "器械",
            "software": "软件",
            "digital": "数字化",
            "remote": "远程",
            "monitoring": "监测",
            "wearable": "可穿戴",
            "China": "中国",
            "US": "美国",
            "Europe": "欧洲",
            "Japan": "日本",
            "class I": "一类",
            "class II": "二类",
            "class III": "三类",
            "510(k)": "510(k)审批",
            "PMA": "PMA审批",
            "CE mark": "CE标志",
            "NMPA": "国家药监局",
            "recall": "召回",
            "safety": "安全",
            "risk": "风险",
            "benefit": "获益",
            "reimbursement": "医保报销",
            "coverage": "覆盖",
            "market": "市场",
            "revenue": "营收",
            "acquisition": "收购",
            "partnership": "合作",
            "investment": "投资",
            "funding": "融资",
            "startup": "创业公司",
            "innovation": "创新",
            "breakthrough": "突破",
            "first": "首个",
            "new": "新",
            "latest": "最新",
            "report": "报告",
            "announce": "宣布",
            "says": "称",
        }
        result = title
        for k, v in trans.items():
            result = result.replace(k, v)
        result = result.replace(", ", " ").replace(".", "").replace("  ", " ")
        return result.strip()

    def _generate_ai_summary(self, title, snippet):
        """
        使用DeepSeek AI理解新闻内容，生成中文摘要
        优先使用AI，失败后使用规则引擎
        """
        api_key = self.config.get("deepseek_api_key", "")
        clean_title = self._clean_title(title)
        clean_snippet = self._clean_html(snippet)

        # 首先尝试使用规则引擎生成高质量摘要
        rule_summary = self._polish_summary("", clean_title, clean_snippet)
        if rule_summary and len(rule_summary) > 20 and not rule_summary.startswith("Towards intelligent") and not rule_summary.startswith("The most innovative"):
            print(f"[摘要] 规则引擎生成")
            return rule_summary

        # 如果规则引擎效果不好，尝试AI
        if not api_key:
            # 翻译摘要
            translated = self._translate_to_chinese(clean_snippet[:500])
            if translated:
                return translated[:120]
            return rule_summary or "暂无摘要"

        prompt = f"""你是一个专业的医疗器械新闻分析师。请为以下新闻写一个简洁的中文摘要（60-80字）。

标题：{clean_title}
内容：{clean_snippet[:600]}

要求：
1. 包含公司/产品/事件/意义
2. 涉及金额要换算（如$50M=5000万美元）
3. 只输出摘要，不要解释

摘要："""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的医疗器械行业分析师。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 150
            }

            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                summary = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if summary:
                    # 清理AI输出
                    summary = summary.replace("摘要：", "").replace("摘要:", "").strip()
                    print(f"[AI摘要] DeepSeek生成成功")
                    return summary
            elif response.status_code == 402:
                print(f"[AI摘要] API余额不足")
            else:
                print(f"[AI摘要] API错误: {response.status_code}")

        except Exception as e:
            print(f"[AI摘要] 请求失败: {str(e)[:30]}")

        # 降级：翻译摘要
        translated = self._translate_to_chinese(clean_snippet[:500])
        if translated:
            return translated[:120]
        return rule_summary or "暂无摘要"

    def _polish_summary(self, translated_text, original_title, original_snippet):
        """
        使用规则引擎生成高质量中文摘要
        根据新闻类型和关键信息生成有意义的摘要
        """
        # 先清理HTML
        clean_snippet = self._clean_html(original_snippet)
        title_lower = original_title.lower()
        snippet_lower = clean_snippet.lower()
        full_text = original_title + " " + clean_snippet

        # 识别新闻类型
        is_fda_approval = any(k in full_text.lower() for k in ['fda approval', 'fda cleared', 'fda clearance', 'fda 获批', '510(k)', 'pma approval', 'de novo'])
        is_nmpa_approval = any(k in full_text for k in ['nmpa', '国家药监局', '药监局批准', '器审中心', '创新器械', '优先审批', '注册证'])
        is_funding = any(k in full_text.lower() for k in ['raises', 'funding round', 'series ', 'closes ', 'billion', 'million'])
        is_acquisition = any(k in full_text.lower() for k in ['acquire', 'acquisition', 'merger', '收购', '并购', '合并'])
        is_product_launch = any(k in full_text.lower() for k in ['launches', 'launch', 'introduces', '上市', '发布', 'commercial launch'])
        is_clinical = any(k in full_text.lower() for k in ['clinical trial', 'clinical study', 'phase', '入组', '入组完成'])
        is_robot = any(k in full_text.lower() for k in ['surgical robot', 'robotic surgery', 'da vinci', 'versius'])
        is_ai = any(k in full_text.lower() for k in ['ai-powered', 'ai-based', 'artificial intelligence', 'machine learning', 'deep learning'])
        is_recall = any(k in full_text.lower() for k in ['recall', '召回', 'safety notice', '警戒'])
        is_regulation = any(k in full_text.lower() for k in ['reimbursement', 'cms', 'drg', 'dip', '集中采购', '带量采购'])

        summary_parts = []

        # 提取公司名称（中英文映射）
        company_en_cn = {
            'medtronic': '美敦力', 'abbott': '雅培', 'philips': '飞利浦', 'ge healthcar': 'GE医疗',
            'siemens healthineer': '西门子医疗', 'siemens': '西门子', 'boston scientific': '波士顿科学',
            'stryker': '史赛克', 'johnson & johnson': '强生', 'jj': '强生', 'roche': '罗氏',
            'edwards lifescien': '爱德华兹', 'edwards': '爱德华兹', 'becton dickinson': 'BD',
            'bd': 'BD', 'terumo': '泰尔茂', 'cook medical': '库克医疗', 'cook': '库克',
            'microport': '微创', 'crrt': '微创', 'novo nordisk': '诺和诺德', 'eli lilly': '礼来',
            'johnson': '强生', 'apple': '苹果', 'google': '谷歌', 'amazon': '亚马逊',
            'j&j medtech': '强生医疗', 'j&j': '强生'
        }
        company = ""
        for en, cn in company_en_cn.items():
            if en in title_lower:
                company = cn
                break

        # 提取金额
        amount = ""
        import re
        money_match = re.search(r'\$(\d+\.?\d*)\s*(billion|million|B|M)', full_text, re.I)
        if not money_match:
            money_match = re.search(r'(\d+\.?\d*)\s*(billion|million)\s*(dollar|美元)', full_text, re.I)
        if money_match:
            num = float(money_match.group(1))
            unit = money_match.group(2).lower()
            if 'b' in unit:
                amount = f"{num*1000:.0f}亿美元"
            else:
                amount = f"{num:.0f}亿美元" if num >= 10 else f"{num*1000:.0f}万美元"

        # 提取产品类型
        product_type = ""
        if any(k in full_text.lower() for k in ['stent', '支架']):
            product_type = "支架"
        elif any(k in full_text.lower() for k in ['pacemaker', '起搏器', 'defibrillator', '除颤']):
            product_type = "起搏器/除颤"
        elif any(k in full_text.lower() for k in ['robot', '机器人', 'surgical']):
            product_type = "手术机器人"
        elif any(k in full_text.lower() for k in ['catheter', '导管', 'aspiration']):
            product_type = "导管"
        elif any(k in full_text.lower() for k in ['monitor', '监测', '监护', 'vital sign']):
            product_type = "监护设备"
        elif any(k in full_text.lower() for k in ['insulin pump', '胰岛素泵']):
            product_type = "胰岛素泵"
        elif any(k in full_text.lower() for k in ['valve', '瓣膜']):
            product_type = "心脏瓣膜"
        elif any(k in full_text.lower() for k in ['vad', '心室辅助']):
            product_type = "心室辅助"
        elif any(k in full_text.lower() for k in ['pulse', '消融', 'ablation']):
            product_type = "消融产品"

        # 根据新闻类型构建摘要
        if is_fda_approval:
            if company and product_type:
                summary_parts.append(f"{company}{product_type}获FDA批准")
            elif company:
                summary_parts.append(f"{company}产品获FDA批准")
            else:
                summary_parts.append(f"医疗器械获FDA批准上市")
            if amount:
                summary_parts[0] += f"，涉及金额{amount}"

        elif is_nmpa_approval:
            if company and product_type:
                summary_parts.append(f"{company}{product_type}获NMPA批准")
            elif company:
                summary_parts.append(f"{company}产品获NMPA批准")
            else:
                summary_parts.append(f"医疗器械获NMPA批准上市")

        elif is_funding:
            if company:
                summary_parts.append(f"{company}完成{amount}融资")
            else:
                summary_parts.append(f"医疗器械公司完成{amount}融资")
            if is_ai:
                summary_parts[0] += "，加码AI医疗"
            elif is_robot:
                summary_parts[0] += "，布局手术机器人"
            elif product_type:
                summary_parts[0] += f"，深耕{product_type}领域"

        elif is_acquisition:
            if company:
                summary_parts.append(f"{company}发起收购交易")
            else:
                summary_parts.append(f"医疗器械行业收购交易")
            if amount:
                summary_parts[0] += f"，涉及金额{amount}"

        elif is_product_launch:
            if company and product_type:
                summary_parts.append(f"{company}{product_type}在美国上市")
            elif product_type:
                summary_parts.append(f"{product_type}在美国上市")
            else:
                summary_parts.append(f"医疗器械新品上市")

        elif is_clinical:
            if company and product_type:
                summary_parts.append(f"{company}{product_type}临床试验取得进展")
            elif product_type:
                summary_parts.append(f"{product_type}临床试验新数据发布")
            else:
                summary_parts.append(f"医疗器械临床试验有新进展")

        elif is_recall:
            if company:
                summary_parts.append(f"{company}发起产品召回")
            else:
                summary_parts.append(f"医疗器械产品被召回")

        elif is_ai:
            if company:
                summary_parts.append(f"AI医疗器械：{company}推新产品")
            else:
                summary_parts.append(f"AI医疗器械创新产品获批")

        elif is_robot:
            if company:
                summary_parts.append(f"{company}手术机器人有新进展")
            else:
                summary_parts.append(f"手术机器人领域新动态")

        elif is_regulation:
            summary_parts.append(f"医疗器械政策动态：集采/医保调整")

        else:
            # 通用摘要：从clean_snippet中提取关键句子
            if len(clean_snippet) > 20:
                # 截取有意义的长度
                summary = clean_snippet[:150].rsplit(' ', 1)[0]
                summary_parts.append(summary)
            elif translated_text and len(translated_text) > 20:
                summary_parts.append(translated_text[:100])
            else:
                summary_parts.append(original_title[:60])

        result = "".join(summary_parts)
        # 清理可能的HTML残留
        result = re.sub(r'<[^>]+>', '', result)
        return result if result else clean_snippet[:80]

    def _extract_product_name(self, title):
        """从标题中提取产品名称"""
        # 常见产品模式
        patterns = [
            r'(Versius Plus [^\s]+)',
            r'(da Vinci [^\s]+)',
            r'(Magenta-[^\s]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:system|platform|device|robot|catheter|implant)',
            r'([^\s]+\s+[^\s]+)\s+(?:FDA|NMPA|CE)',
        ]
        import re
        for pattern in patterns:
            match = re.search(pattern, title, re.I)
            if match:
                return match.group(1)[:30]
        # 简单策略：取标题开头的有意义词
        words = title.split()[:4]
        return " ".join(words)[:30] if words else ""

    def _extract_company_name(self, title):
        """从标题中提取公司名称"""
        # 常见公司
        companies = {
            'medtronic': '美敦力', 'abbott': '雅培', 'philips': '飞利浦',
            'johnson': '强生', 'ge': 'GE医疗', 'siemens': '西门子医疗',
            'boston scientific': '波士顿科学', 'stryker': '史赛克',
            'roche': '罗氏', 'abbvie': '艾伯维', 'edwards': '爱德华兹',
            'crrt': '微创', 'tenmed': '天鸿', 'crm': '赛诺医疗'
        }
        title_lower = title.lower()
        for en, cn in companies.items():
            if en in title_lower:
                return cn
        return ""

    def _get_fallback_news(self):
        """Fallback news data"""
        return [
            {"title": "FDA approves new AI diagnostic device", "url": "https://www.fda.gov", "snippet": "FDA approves AI-based diagnostic system", "keyword": "FDA", "region": "Foreign"},
            {"title": "China NMPA approves domestic robot", "url": "https://www.nmpa.gov.cn", "snippet": "Domestic surgical robot receives NMPA approval", "keyword": "NMPA", "region": "China"},
        ]

    def search_news(self):
        """Search medical device news from RSS sources and search engines"""
        print("Starting Medical Device news fetch...")

        all_news = []

        # Search sources (Baidu/Google News)
        search_sources = self.config.get("search_sources", [])
        search_rss = [(s["url"], s["name"], s["region"]) for s in search_sources]

        # Foreign RSS sources
        foreign_sources = self.config.get("foreign_sources", [])
        foreign_rss = [(s["url"], s["name"], s["region"]) for s in foreign_sources]

        # China RSS sources
        china_sources = self.config.get("china_sources", [])
        china_rss = [(s["url"], s["name"], s["region"]) for s in china_sources]

        # Medical device keywords (in both English and Chinese)
        md_kw = [
            'medical device', 'medtech', 'implant', 'surgical robot', 'stent',
            'pacemaker', 'ivd', 'in vitro diagnostic', 'medical equipment',
            'fda approval', 'nmpa', '510(k)', 'ce mark', 'class iii',
            '医疗器械', '手术机器人', '植入物', '体外诊断', '支架', '起搏器',
            '人工关节', '医疗设备', 'FDA批准', 'NMPA', '创新器械'
        ]

        # Fetch from search engines (Baidu/Google)
        print("\n=== Fetching from Search Engines ===")
        for url, src, region in search_rss:
            try:
                print(f"[Search] {src}")
                resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    for ent in feed.entries[:20]:
                        title = self._clean_title(ent.get('title', ''))
                        summary = ent.get('summary', '') or ent.get('description', '') or ent.get('content', '')
                        link = ent.get('link', '') or ent.get('id', '')

                        # Skip if no title or link
                        if not title or not link:
                            continue

                        # Check if already have this news
                        if any(n.get('url') == link for n in all_news):
                            continue

                        all_news.append({
                            "title": title,
                            "url": link,
                            "snippet": self._clean_html(summary[:300]) if summary else '',
                            "keyword": src,
                            "region": region,
                            "published": ent.get('published', '') or ent.get('updated', '')
                        })
                    print(f"  Found {len(feed.entries)} entries from {src}")
            except Exception as e:
                print(f"  Error: {str(e)[:50]}")

        # Fetch foreign news
        print("\n=== Fetching Foreign Sources ===")
        for url, src, region in foreign_rss:
            try:
                print(f"[Get] {src}")
                resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    for ent in feed.entries[:15]:
                        title = self._clean_title(ent.get('title', ''))
                        summary = ent.get('summary', '') or ent.get('description', '')
                        content = (title + ' ' + summary).lower()
                        if any(k.lower() in content for k in md_kw):
                            pub = ""
                            if hasattr(ent, 'published'):
                                pub = ent.published
                            all_news.append({
                                "title": title,
                                "url": ent.get('link', ''),
                                "snippet": self._clean_html(summary[:300]) if summary else '',
                                "keyword": src,
                                "region": region,
                                "published": pub
                            })
            except Exception as e:
                print(f"  Error: {str(e)[:50]}")

        # Fetch China news
        print("\n=== Fetching China Sources ===")
        for url, src, region in china_rss:
            try:
                print(f"[Get] {src}")
                resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content.decode('utf-8', errors='ignore'))
                    for ent in feed.entries[:15]:
                        title = self._clean_title(ent.get('title', ''))
                        summary = ent.get('summary', '') or ent.get('description', '')
                        content = (title + ' ' + summary).lower()
                        if any(k.lower() in content for k in md_kw):
                            pub = ""
                            if hasattr(ent, 'published'):
                                pub = ent.published
                            all_news.append({
                                "title": title,
                                "url": ent.get('link', ''),
                                "snippet": self._clean_html(summary[:300]) if summary else '',
                                "keyword": src,
                                "region": region,
                                "published": pub
                            })
            except Exception as e:
                print(f"  Error: {str(e)[:50]}")

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
            "Regulatory/批准": ["FDA", "NMPA", "approval", "approved", "clearance", "cleared", "CE", "510(k)", "PMA", "批准", "获批", "注册"],
            "AI/Digital/数字化": ["AI", "digital", "software", "app", "remote", "人工智能", "软件", "数字", "互联网"],
            "Surgical Robot/手术机器人": ["robot", "robotic", "surgical", "da Vinci", "手术机器人", "腔镜", "导航"],
            "Implant/植入器械": ["implant", "stent", "pacemaker", "prosthetic", "joint", "支架", "起搏器", "关节", "植入"],
            "IVD/体外诊断": ["IVD", "diagnostic", "test", "PCR", "试剂", "诊断", "检测"],
            "Market/Business/市场商业": ["market", "revenue", "acquisition", "funding", "investment", "partnership", "收购", "融资", "合作", "市场"]
        }

        result = {k: [] for k in cats}
        result["Other/其他"] = []

        for news in self.news_data:
            title = news.get("title", "")
            matched = False
            for cat, kws in cats.items():
                if any(k.lower() in title.lower() for k in kws):
                    result[cat].append(news)
                    matched = True
                    break
            if not matched:
                result["Other/其他"].append(news)

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
            icon_map = {
                "Regulatory/批准": "REG",
                "AI/Digital/数字化": "AI",
                "Surgical Robot/手术机器人": "ROBOT",
                "Implant/植入器械": "IMPLANT",
                "IVD/体外诊断": "IVD",
                "Market/Business/市场商业": "BIZ"
            }
            icon = icon_map.get(cat, "NEWS")
            cat_html += f'<span class="cat-tag">{icon} {cat} ({cnt})</span>'

        chinese_highlights = self._get_chinese_highlights()

        self.summary = f'''
    <div class="summary-section">
        <h2>Medical Device Daily Highlights</h2>
        <div class="category-tags">{cat_html}</div>

        <div class="chinese-summary">
            <h3>Top 10 Medical Device News</h3>
            {chinese_highlights}
        </div>
    </div>'''

    def _get_chinese_highlights(self):
        """Get Chinese highlights - 使用AI理解生成中文摘要"""
        highlights = ""

        for i, news in enumerate(self.news_data[:10], 1):
            title = news.get("title", "")
            snippet = news.get("snippet", "")[:300]
            url = news.get("url", "")
            pub = self._format_date(news.get("published", ""))
            src = news.get("keyword", "")
            region = news.get("region", "Foreign")

            # 使用AI生成中文摘要
            ai_summary = self._generate_ai_summary(title, snippet)

            # 翻译标题
            chinese_title = self._translate_to_chinese(title)
            if not chinese_title:
                chinese_title = self._translate_title(title)

            region_label = "🌍 海外" if region == "Foreign" else "🇨🇳 国内"

            highlights += f'''
            <div class="highlight-item">
                <span class="highlight-num">{i}</span>
                <div class="highlight-content">
                    <div class="highlight-title">
                        <a href="{url}" target="_blank" style="color: #333; text-decoration: none;">{chinese_title}</a>
                    </div>
                    <p class="highlight-snippet" style="color: #444; font-size: 13px; margin: 8px 0; line-height: 1.5; font-weight: 500;">{ai_summary}</p>
                    <div class="highlight-meta">
                        <span class="highlight-date">{pub}</span> |
                        <span class="highlight-source">{src}</span> |
                        <span style="color: #1976d2;">{region_label}</span>
                    </div>
                </div>
            </div>'''

        return highlights

    def _generate_top10_html(self, news_list, section_name, section_class):
        """Generate Top10 HTML for news list - 使用AI理解生成中文摘要"""
        items_html = ""
        for i, news in enumerate(news_list[:10], 1):
            title = news.get("title", "")
            snippet = news.get("snippet", "")[:300]
            url = news.get("url", "")
            pub = self._format_date(news.get("published", ""))

            # 使用AI生成中文摘要（不是简单翻译）
            ai_summary = self._generate_ai_summary(title, snippet)

            # 翻译标题作为链接显示
            chinese_title = self._translate_to_chinese(title)
            if not chinese_title:
                chinese_title = self._translate_title(title)

            items_html += f'''
            <div class="top10-item">
                <span class="top10-num">{i}</span>
                <div class="top10-content">
                    <div class="top10-title"><a href="{url}" target="_blank">{chinese_title}</a></div>
                    <div class="top10-desc">{ai_summary}</div>
                    <div class="top10-meta">
                        <span class="top10-date">{pub}</span>
                    </div>
                </div>
            </div>'''

        return f'''
    <div class="top10-section {section_class}">
        <h2>{section_name}</h2>
        <div class="top10-list">{items_html}
        </div>
    </div>'''

    def _generate_chinese_top10_html(self):
        """Generate Top10 summaries for China and Global"""
        china_news = [n for n in self.news_data if n.get("region") == "China"]
        global_news = [n for n in self.news_data if n.get("region") == "Foreign"]

        china_html = self._generate_top10_html(china_news, "🇨🇳 国内医疗器械新闻 Top 10", "top10-china") if china_news else ""
        global_html = self._generate_top10_html(global_news, "🌍 海外医疗器械新闻 Top 10", "top10-global") if global_news else ""

        return china_html + global_html

    def generate_html_report(self):
        """Generate HTML report"""
        today = datetime.now().strftime("%Y-%m-%d")

        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>医疗器械新闻 - {date}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #00acc1 0%, #00838f 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .top10-section {{ background: white; padding: 25px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .top10-section h2 {{ margin: 0 0 15px 0; color: #1a1a1a; font-size: 20px; padding-bottom: 10px; border-bottom: 2px solid #00acc1; }}
        .top10-china {{ border-left: 4px solid #e53935; }}
        .top10-china h2 {{ border-bottom-color: #e53935; }}
        .top10-china .top10-item {{ background: #fff5f5; border-left-color: #e53935; }}
        .top10-china .top10-num {{ background: #e53935; }}
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
        .top10-title a:hover {{ color: #00acc1; }}
        .top10-desc {{ font-size: 13px; color: #444; line-height: 1.6; margin-top: 6px; font-weight: 500; }}
        .top10-meta {{ font-size: 12px; color: #888; margin-top: 4px; }}
        .summary-section {{ background: white; padding: 25px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .summary-section h2 {{ margin: 0 0 20px 0; color: #1a1a1a; font-size: 20px; padding-bottom: 15px; border-bottom: 2px solid #00acc1; }}
        .category-tags {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
        .cat-tag {{ background: linear-gradient(135deg, #00acc1 0%, #00838f 100%); color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px; }}
        .highlight-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .highlight-item {{ display: flex; align-items: flex-start; gap: 12px; padding: 15px; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #00acc1; }}
        .highlight-num {{ background: #00acc1; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: bold; flex-shrink: 0; }}
        .highlight-content {{ flex: 1; }}
        .highlight-title {{ font-size: 16px; font-weight: 600; color: #333; line-height: 1.5; margin-bottom: 5px; }}
        .highlight-snippet {{ font-size: 13px; color: #666; line-height: 1.5; margin: 5px 0; }}
        .highlight-meta {{ font-size: 13px; color: #888; }}
        .chinese-summary {{ margin-top: 20px; }}
        .chinese-summary h3 {{ color: #333; font-size: 18px; margin-bottom: 15px; }}
        .news-item {{ background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .news-date {{ color: #999; font-size: 12px; margin-bottom: 5px; }}
        .news-item h3 {{ margin: 0 0 10px 0; color: #333; }}
        .news-item a {{ color: #00acc1; text-decoration: none; }}
        .snippet {{ color: #666; font-size: 14px; line-height: 1.6; }}
        .tag {{ display: inline-block; background: #e8f4f8; color: #2a7bb0; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 8px; }}
        .tag-china {{ background: #ffeaea; color: #d32f2f; }}
        .tag-foreign {{ background: #e3f2fd; color: #1976d2; }}
        .news-meta {{ margin-top: 10px; display: flex; align-items: center; flex-wrap: wrap; gap: 5px; }}
        .section-title {{ font-size: 16px; font-weight: bold; color: #333; margin: 20px 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #00acc1; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>医疗器械新闻 Daily</h1>
        <p>{date} | {count} articles</p>
    </div>

    {chinese_top10}

    {summary}

    <div class="section-title">[All News]</div>
    {news_html}
    <div class="footer">
        Generated by Medical Device News Assistant
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
            <a href="{url}" target="_blank">原文</a>
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

    def _send_email(self, html_content, max_retries=3, retry_delay=5):
        """Send HTML report via email with retry mechanism"""
        smtp_server = self.config.get("smtp_server", "smtp.163.com")
        smtp_port = self.config.get("smtp_port", 465)
        smtp_user = self.config.get("smtp_user", "")
        smtp_password = self.config.get("smtp_password", "")
        recipient = self.config.get("recipient_email", "")
        enable_email = self.config.get("enable_email", False)

        if not enable_email:
            print("[Email] Email sending is disabled")
            return True

        if not smtp_user or not smtp_password or not recipient:
            print("[Email] Email config incomplete, skip sending")
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"医疗器械新闻 Daily - {today}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = smtp_user
        msg['To'] = recipient

        plain_text = f"医疗器械新闻 Daily - {today}\n\n请查看HTML版本获取完整内容。"
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

    def save_report(self):
        """Save report to file"""
        out_folder = self.config.get("output_folder",
            os.path.join(os.path.dirname(__file__), "output"))

        today = datetime.now().strftime("%Y-%m-%d")
        day_folder = os.path.join(out_folder, today)
        os.makedirs(day_folder, exist_ok=True)

        # Generate Chinese Top10
        self.chinese_summary = self._generate_chinese_top10_html()

        html_content = self.generate_html_report()

        html_path = os.path.join(day_folder, "medical_news.html")
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

    def run(self):
        """Run news collection"""
        try:
            self.search_news()
            folder = self.save_report()
            return 0
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(description="Medical Device News Daily")
    parser.add_argument("--config", default="config/medical_device_config.json", help="Config path")
    parser.add_argument("--test", action="store_true", help="Test")

    args = parser.parse_args()

    news = MedicalDeviceNews(args.config)

    if args.test:
        print("Testing...")
        news.search_news()
    else:
        return news.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
