#!/usr/bin/env python3
"""
Medical Device News Daily - 医疗器械新闻日报
Daily medical device news collection and HTML report generation
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
except ImportError:
    print("Error: Please install requests and feedparser")
    sys.exit(1)


DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


class MedicalDeviceNews:
    """医疗器械新闻日报生成器"""

    # Source credibility weights (med-device domain)
    SOURCE_CREDIBILITY = {
        'FDA': 100, 'NMPA': 95, 'MedTech Dive': 85, 'MassDevice': 85,
        'FierceMedTech': 80, 'Fierce Biotech': 75, 'Medgadget': 75,
        'Medical Device Network': 80, 'MD+DI': 80, 'Medscape': 75,
        'Becker\'s': 70, 'Reuters': 65, 'STAT News': 75,
        'Evaluate Vantage': 75, 'BioSpace': 65,
        'Baidu News': 60, 'Google News': 65,
        '药智网': 60, '医疗器械信息': 60, '中国医疗器械': 65,
        '器械之家': 60, '赛柏蓝': 55,
    }

    # Region classification keywords
    REGION_KEYWORDS = {
        '美国': ['USA', 'United States', 'America', 'US ', 'U.S.', 'FDA',
                 'Medtronic', 'Abbott', 'Stryker', 'Boston Scientific',
                 'Johnson & Johnson', 'Edwards Lifesciences', 'Intuitive Surgical',
                 'Zimmer', 'BD', 'Dexcom', 'Insulet'],
        '欧洲': ['EU', 'European', 'UK', 'Britain', 'London', 'Germany', 'France',
                 'EMA', 'Siemens', 'Philips', 'Roche', 'Smith & Nephew',
                 'Fresenius', 'Coloplast', 'Getinge'],
        '中国': ['China', 'Chinese', 'Beijing', 'Shanghai', 'Shenzhen', 'Hong Kong',
                 'NMPA', '药监局', '器审中心', '微创', '迈瑞', '乐普',
                 '威高', '启明', '赛诺', '华大', '鱼跃'],
        '国际': ['Japan', 'Korea', 'India', 'Singapore', 'Australia', 'Canada',
                 'global', 'worldwide', 'Israel', 'Terumo', 'Olympus']
    }

    # Industry news keywords (med-device domain)
    INDUSTRY_KEYWORDS = ['FDA approval', 'FDA clearance', 'FDA cleared', '510(k)',
                         'PMA', 'De Novo', 'CE mark', 'NMPA', 'approval',
                         'recall', '召回', 'safety notice',
                         'acquisition', 'merger', 'acquire', 'merge',
                         'funding', 'investment', 'Series ', 'IPO',
                         'reimbursement', 'CMS', 'Medicare', 'coverage',
                         'clinical trial', 'clinical study', 'phase',
                         'launch', 'commercial', 'partnership', 'deal',
                         'patent', 'spin off', 'spinoff', 'restructuring',
                         '集采', '带量采购', '注册证', '创新器械']

    def __init__(self, config_path="config/medical_device_config.json"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_path = os.path.dirname(os.path.dirname(current_dir))
        self.config_path = os.path.join(self.base_path, config_path)
        self.email_config_path = os.path.join(self.base_path, "config/email_config.json")
        self.config = self._load_news_config()
        self.news_data = []

    def _load_news_config(self):
        config_file = os.path.join(self.base_path, "config/medical_device_config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_email_config(self):
        if os.path.exists(self.email_config_path):
            with open(self.email_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _clean_html(self, text):
        if not text:
            return ""
        text = re.sub(r'<[^>]*>', '', text)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&apos;', "'")
        text = ' '.join(text.split())
        return text.strip()

    def _clean_title(self, title):
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
        content = (title + ' ' + snippet).lower()
        if region_tag == 'China':
            return '中国'
        for region, keywords in self.REGION_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content:
                    return region
        return '国际'

    def _calculate_priority(self, news_item):
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
        content = (title + ' ' + snippet).lower()
        for kw in self.INDUSTRY_KEYWORDS:
            if kw.lower() in content:
                return True
        return False

    def _format_snippet(self, snippet, max_len=120):
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

    def _translate_to_chinese(self, text):
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
        trans = {
            "FDA": "美国FDA", "approval": "批准", "approved": "已批准",
            "clearance": "获批", "cleared": "已获批", "launch": "上市",
            "launches": "上市", "recall": "召回", "clinical trial": "临床试验",
            "study": "研究", "device": "器械", "implant": "植入物",
            "surgical": "外科", "robot": "机器人", "AI": "人工智能",
            "diagnostic": "诊断", "healthcare": "医疗", "hospital": "医院",
            "patient": "患者", "treatment": "治疗", "therapy": "疗法",
            "software": "软件", "digital": "数字化", "remote": "远程",
            "monitoring": "监测", "wearable": "可穿戴",
            "China": "中国", "US": "美国", "Europe": "欧洲", "Japan": "日本",
            "class I": "一类", "class II": "二类", "class III": "三类",
            "510(k)": "510(k)审批", "PMA": "PMA审批", "CE mark": "CE标志",
            "NMPA": "国家药监局", "safety": "安全", "risk": "风险",
            "benefit": "获益", "reimbursement": "医保报销",
            "coverage": "覆盖", "market": "市场", "revenue": "营收",
            "acquisition": "收购", "partnership": "合作", "investment": "投资",
            "funding": "融资", "startup": "创业公司", "innovation": "创新",
            "breakthrough": "突破", "first": "首个", "new": "新",
            "latest": "最新", "report": "报告", "announce": "宣布",
            "says": "称", "million": "百万", "billion": "十亿",
        }
        result = title
        sorted_trans = sorted(trans.items(), key=lambda x: len(x[0]), reverse=True)
        for k, v in sorted_trans:
            result = result.replace(k, v)
        result = result.replace(", ", " ").replace(".", "").replace("  ", " ")
        return result.strip()

    def _generate_ai_summary(self, title, snippet):
        """使用DeepSeek AI理解新闻内容，生成中文摘要"""
        api_key = self.config.get("deepseek_api_key", "")
        clean_title = self._clean_title(title)
        clean_snippet = self._clean_html(snippet)

        rule_summary = self._polish_summary("", clean_title, clean_snippet)
        if rule_summary and len(rule_summary) > 20 and not rule_summary.startswith("Towards intelligent") and not rule_summary.startswith("The most innovative"):
            print(f"[摘要] 规则引擎生成")
            return rule_summary

        if not api_key:
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
                    summary = summary.replace("摘要：", "").replace("摘要:", "").strip()
                    print(f"[AI摘要] DeepSeek生成成功")
                    return summary
            elif response.status_code == 402:
                print(f"[AI摘要] API余额不足")
            else:
                print(f"[AI摘要] API错误: {response.status_code}")
        except Exception as e:
            print(f"[AI摘要] 请求失败: {str(e)[:30]}")

        translated = self._translate_to_chinese(clean_snippet[:500])
        if translated:
            return translated[:120]
        return rule_summary or "暂无摘要"

    def _polish_summary(self, translated_text, original_title, original_snippet):
        """使用规则引擎生成高质量中文摘要"""
        clean_snippet = self._clean_html(original_snippet)
        title_lower = original_title.lower()
        snippet_lower = clean_snippet.lower()
        full_text = original_title + " " + clean_snippet

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

        amount = ""
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
            if len(clean_snippet) > 20:
                summary = clean_snippet[:150].rsplit(' ', 1)[0]
                summary_parts.append(summary)
            elif translated_text and len(translated_text) > 20:
                summary_parts.append(translated_text[:100])
            else:
                summary_parts.append(original_title[:60])

        result = "".join(summary_parts)
        result = re.sub(r'<[^>]+>', '', result)
        return result if result else clean_snippet[:80]

    def _extract_product_name(self, title):
        patterns = [
            r'(Versius Plus [^\s]+)',
            r'(da Vinci [^\s]+)',
            r'(Magenta-[^\s]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:system|platform|device|robot|catheter|implant)',
            r'([^\s]+\s+[^\s]+)\s+(?:FDA|NMPA|CE)',
        ]
        for pattern in patterns:
            match = re.search(pattern, title, re.I)
            if match:
                return match.group(1)[:30]
        words = title.split()[:4]
        return " ".join(words)[:30] if words else ""

    def _extract_company_name(self, title):
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
        return [
            {"title": "FDA approves new AI diagnostic device", "url": "https://www.fda.gov",
             "snippet": "FDA approves AI-based diagnostic system", "keyword": "FDA", "region": "Foreign"},
            {"title": "China NMPA approves domestic robot", "url": "https://www.nmpa.gov.cn",
             "snippet": "Domestic surgical robot receives NMPA approval", "keyword": "NMPA", "region": "China"},
        ]

    def search_news(self):
        """Search medical device news from RSS sources and search engines"""
        print("Starting Medical Device news fetch...")

        all_news = []

        search_sources = self.config.get("search_sources", [])
        search_rss = [(s["url"], s["name"], s["region"]) for s in search_sources]

        foreign_sources = self.config.get("foreign_sources", [])
        foreign_rss = [(s["url"], s["name"], s["region"]) for s in foreign_sources]

        china_sources = self.config.get("china_sources", [])
        china_rss = [(s["url"], s["name"], s["region"]) for s in china_sources]

        md_kw = [
            'medical device', 'medtech', 'implant', 'surgical robot', 'stent',
            'pacemaker', 'ivd', 'in vitro diagnostic', 'medical equipment',
            'fda approval', 'nmpa', '510(k)', 'ce mark', 'class iii',
            '医疗器械', '手术机器人', '植入物', '体外诊断', '支架', '起搏器',
            '人工关节', '医疗设备', 'FDA批准', 'NMPA', '创新器械'
        ]

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
                        if not title or not link:
                            continue
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

        # Classify region
        for n in unique:
            n['region'] = self._classify_region(
                n.get('title', ''), n.get('snippet', ''), n.get('region', ''))

        self.news_data = unique
        print(f"\n[Total] {len(unique)} news fetched")
        return unique

    def _categorize_news(self):
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

    def generate_html_report(self):
        """Generate HTML report — allergy-style segmented layout"""
        today = datetime.now().strftime("%Y-%m-%d")
        today_formatted = datetime.now().strftime("%Y年%m月%d日")

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

        # 今日重点: high credibility sources
        top_news = [n for n in us_news_sorted if self.SOURCE_CREDIBILITY.get(n.get('keyword', ''), 0) >= 80][:10]

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
                <div style="background:white; border-left:3px solid #00acc1; padding:12px 15px; margin-bottom:10px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                    <div style="font-weight:600; color:#222; margin-bottom:6px; font-size:14px; line-height:1.4;">
                        <span style="color:#ff9800;">{stars}</span> <a href="{url}" target="_blank" style="color:#00838f; text-decoration:none;">{title_cn}</a>
                    </div>
                    <div style="font-size:12px; color:#555; line-height:1.5; margin-bottom:6px;">{snippet}</div>
                    <div style="font-size:11px; color:#888;">
                        <span style="background:#e0f7fa; color:#006064; padding:2px 6px; border-radius:3px;">{source}</span>
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
            return f'<li style="margin-bottom:8px; line-height:1.4;"><a href="{url}" target="_blank" style="color:#00838f; text-decoration:none;">{title_cn}</a><span style="color:#999; font-size:11px;">{time_str}</span></li>'

        top_news_html = ''.join([render_news_card(n) for n in top_news]) if top_news else '<div style="color:#999; padding:20px; text-align:center;">暂无重点新闻</div>'

        international = us_news_sorted + eu_news_sorted + intl_news_sorted
        international_sorted = sorted(international, key=self._calculate_priority, reverse=True)
        intl_html = ''.join([render_simple_news_item(n) for n in international_sorted[:20]])

        china_html = ''.join([render_simple_news_item(n) for n in china_news_sorted[:15]])

        industry_html = ''.join([render_simple_news_item(n) for n in industry_news_sorted[:10]])

        us_count = len(us_news)
        eu_count = len(eu_news)
        china_count = len(china_news)
        intl_count = len(international_sorted)
        industry_count = len(industry_news)

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>医疗器械新闻日报 - {today}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; max-width:800px; margin:0 auto; padding:15px; background:#f5f5f5; }}
        .header {{ background:linear-gradient(135deg, #00acc1 0%, #00838f 100%); color:white; padding:20px 25px; border-radius:12px; margin-bottom:20px; box-shadow:0 4px 12px rgba(0,131,143,0.3); }}
        .header h1 {{ margin:0; font-size:22px; display:flex; align-items:center; gap:8px; }}
        .header .date {{ margin:8px 0 0 0; opacity:0.9; font-size:14px; }}
        .header .stats {{ display:flex; gap:10px; margin-top:12px; flex-wrap:wrap; }}
        .header .stats span {{ background:rgba(255,255,255,0.2); padding:5px 12px; border-radius:15px; font-size:12px; }}
        .section {{ background:white; border-radius:10px; padding:18px 20px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
        .section h2 {{ color:#333; font-size:15px; margin:0 0 12px 0; padding-bottom:8px; border-bottom:2px solid #eee; display:flex; align-items:center; gap:6px; }}
        .section h2 .count {{ font-size:12px; color:#999; font-weight:normal; margin-left:auto; }}
        .news-list {{ list-style:none; padding:0; margin:0; }}
        .footer {{ text-align:center; color:#bbb; margin-top:20px; font-size:11px; }}
        a {{ color:#00838f; text-decoration:none; }}
        a:hover {{ text-decoration:underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 医疗器械新闻日报 {today}</h1>
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
        <h2>🔥 今日重点 <span class="count">高可信度来源 ★★★★★</span></h2>
        {top_news_html}
    </div>

    <div class="section">
        <h2>🌍 国际动态 <span class="count">{intl_count}条</span></h2>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0 20px;">
            <ul class="news-list">{intl_html[:len(intl_html)//2] if intl_html else ''}</ul>
            <ul class="news-list">{intl_html[len(intl_html)//2:] if intl_html else ''}</ul>
        </div>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：FDA / MedTech Dive / MassDevice / FierceMedTech</div>
    </div>

    <div class="section">
        <h2>🇨🇳 中国动态 <span class="count">{china_count}条</span></h2>
        <ul class="news-list">{china_html if china_html else '<li style="color:#999;">暂无中国新闻</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：NMPA / 医疗器械信息 / 药智网</div>
    </div>

    <div class="section">
        <h2>📈 行业快讯 <span class="count">{industry_count}条</span></h2>
        <ul class="news-list">{industry_html if industry_html else '<li style="color:#999;">暂无行业快讯</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">审批 / 融资 / 并购 / 召回 / 上市</div>
    </div>

    <div class="footer">
        <p>由 Medical Device News Daily 自动生成 · {today}</p>
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
                subject = f"🔧 医疗器械 日报 {today} ({count}条)"

            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = smtp_user
            msg['To'] = recipient

            plain_text = f"医疗器械新闻日报 - {today}\n共 {count} 条\n\n请查看HTML版本获取完整内容。"
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
        out_folder = os.path.join(os.path.dirname(__file__), "output")

        today = datetime.now().strftime("%Y-%m-%d")
        day_folder = os.path.join(out_folder, today)
        os.makedirs(day_folder, exist_ok=True)

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

        if send_email:
            self._send_email(html_content)

        return day_folder

    def run(self, send_email=True):
        try:
            self.search_news()
            folder = self.save_report(send_email=send_email)
            return 0
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(description="Medical Device News Daily - 医疗器械新闻日报")
    parser.add_argument("--config", default="config/medical_device_config.json", help="Config path")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    parser.add_argument("--test", action="store_true", help="Test mode")

    args = parser.parse_args()

    news = MedicalDeviceNews(args.config)

    if args.test:
        print("Testing...")
        news.search_news()
    else:
        return news.run(send_email=not args.no_email)

    return 0


if __name__ == "__main__":
    sys.exit(main())
