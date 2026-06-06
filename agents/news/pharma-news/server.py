#!/usr/bin/env python3
"""
Pharma News Daily - 医药生物制药新闻日报
Daily pharma/biotech news collection and HTML report generation
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


class PharmaNews:
    """医药生物制药新闻日报生成器"""

    # Source credibility weights (pharma domain)
    SOURCE_CREDIBILITY = {
        'STAT News': 95, 'FiercePharma': 90, 'FierceBiotech': 90,
        'BioSpace': 85, 'Evaluate Vantage': 80, 'Endpoints News': 85,
        'BBC Health': 70, 'Reuters Health': 75, 'Nature': 95, 'Science': 95,
        'The Lancet': 95, 'NEJM': 95, 'JAMA': 95,
        '医药网': 65, '药时代': 60, '生物探索': 55, '中国医疗器械': 55,
    }

    # Region classification keywords
    REGION_KEYWORDS = {
        '美国': ['USA', 'United States', 'America', 'US ', 'U.S.', 'FDA',
                 'Pfizer', 'Moderna', 'Eli Lilly', 'Merck', 'AbbVie', 'Gilead',
                 'Regeneron', 'Amgen', 'Bristol Myers', 'Johnson & Johnson',
                 'Biogen', 'Vertex'],
        '欧洲': ['EU', 'European', 'UK', 'Britain', 'London', 'Germany', 'France',
                 'Paris', 'EMA', 'Roche', 'Novartis', 'AstraZeneca', 'Sanofi',
                 'BioNTech', 'GSK', 'Bayer'],
        '中国': ['China', 'Chinese', 'Beijing', 'Shanghai', 'Shenzhen', 'Hong Kong',
                 'NMPA', '药监局', '百济神州', '药明康德', '信达', '恒瑞',
                 '石药', '复星', '华大', '君实', '康希诺', '科兴'],
        '国际': ['Japan', 'Korea', 'India', 'Singapore', 'Australia', 'Canada',
                 'global', 'worldwide', 'WHO', 'Takeda', 'Daiichi']
    }

    # Industry news keywords (pharma domain)
    INDUSTRY_KEYWORDS = ['acquisition', 'merger', 'acquire', 'merge',
                         'funding', 'investment', 'Series ', 'IPO',
                         'clinical trial', 'phase 1', 'phase 2', 'phase 3',
                         'FDA approval', 'EMA approval', 'NMPA approval',
                         'regulatory', 'launch', 'pipeline', 'deal', 'partnership',
                         'patent', 'royalty', 'license', 'manufacturing',
                         'supply chain', 'shortage', 'pricing', 'reimbursement',
                         'layoff', 'restructuring', 'spin off', 'spinoff',
                         '收购', '并购', '融资', '上市', '临床', '获批',
                         '许可', '合作', '专利', '管线', '集采', '医保']

    def __init__(self, config_path="config/pharma_config.json"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_path = os.path.dirname(os.path.dirname(current_dir))
        self.config_path = os.path.join(self.base_path, config_path)
        self.email_config_path = os.path.join(self.base_path, "config/email_config.json")
        self.config = self._load_news_config()
        self.news_data = []
        self.ai_summaries = {"china": [], "global": []}

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

    def _translate_title(self, title):
        trans = {
            "Pfizer": "[辉瑞]", "Moderna": "[莫德纳]", "BioNTech": "[BioNTech]",
            "AstraZeneca": "[阿斯利康]", "Novartis": "[诺华]", "Roche": "[罗氏]",
            "Merck": "[默克]", "Johnson & Johnson": "[强生]", "Eli Lilly": "[礼来]",
            "BMS": "[百时美施贵宝]", "AbbVie": "[艾伯维]", "Gilead": "[吉利德]",
            "Regeneron": "[再生元]", "Sanofi": "[赛诺菲]", "Amgen": "[安进]",
            "Novavax": "[诺瓦瓦克斯]", "GSK": "[葛兰素史克]", "Bayer": "[拜耳]",
            "FDA": "美国FDA", "EMA": "欧洲EMA", "NMPA": "国家药监局",
            "China": "中国", "Chinese": "中国", "U.S.": "美国", "US": "美国",
            "UK": "英国", "EU": "欧盟",
            "vaccine": "疫苗", "vaccination": "疫苗接种", "drug": "药物",
            "therapy": "疗法", "treatment": "治疗", "clinical": "临床",
            "trial": "试验", "approval": "获批", "approved": "获批",
            "launch": "上市", "release": "发布", "announce": "宣布",
            "study": "研究", "research": "研究", "patient": "患者",
            "cancer": "癌症", "tumor": "肿瘤", "oncology": "肿瘤",
            "diabetes": "糖尿病", "obesity": "肥胖", "Alzheimer": "阿尔茨海默",
            "Parkinson": "帕金森", "cardiovascular": "心血管", "stroke": "中风",
            "immune": "免疫", "biotech": "生物技术", "biopharmaceutical": "生物制药",
            "pharmaceutical": "制药", "mRNA": "mRNA", "antibody": "抗体",
            "protein": "蛋白", "cell therapy": "细胞疗法", "gene therapy": "基因疗法",
            "CRISPR": "CRISPR", "deal": "合作", "acquisition": "收购",
            "merger": "合并", "funding": "融资", "investment": "投资",
            "partnership": "合作", "pipeline": "研发管线", "data": "数据",
            "results": "结果", "phase": "阶段",
            "global": "全球", "world": "世界",
            "million": "百万", "billion": "十亿",
        }
        result = title
        sorted_trans = sorted(trans.items(), key=lambda x: len(x[0]), reverse=True)
        for k, v in sorted_trans:
            result = result.replace(k, v)
        result = result.replace(", ", " ").replace(".", "").replace("  ", " ")
        return result.strip()

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

    def init_openai(self):
        api_key = self.config.get("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
        return api_key if api_key else None

    def init_claude(self):
        api_key = self.config.get("claude_api_key", os.environ.get("CLAUDE_API_KEY", ""))
        return api_key if api_key else None

    def _call_ai_summarize(self, news_list, region="global"):
        region_name = "国内" if region == "china" else "全球"
        print(f"[摘要] 正在使用本地算法生成{region_name}新闻摘要...")
        local_result = self._local_summarize(news_list, region)
        if local_result:
            return local_result

        print(f"[摘要] 本地算法不可用，尝试外部AI API...")
        news_text = ""
        for i, news in enumerate(news_list[:20], 1):
            title = news.get("title", "")
            snippet = news.get("snippet", "")[:300]
            url = news.get("url", "")
            news_text += f"{i}. 【{title}】\n   摘要: {snippet}\n   链接: {url}\n\n"

        prompt = f"""你是一个医药行业专业分析师。请阅读以下{region_name}医药/生物制药新闻，为我生成10条最重要的新闻摘要。

要求：
1. 每条摘要用中文撰写，2-3句话说明核心内容
2. 突出新闻的重要性和影响
3. 包含相关公司和机构名称（用中文）
4. 按重要性排序

新闻列表：
{news_text}

请按以下JSON格式输出（只需JSON，不要其他内容）：
{{
  "summaries": [
    {{"index": 1, "title": "简短中文标题", "summary": "2-3句中文摘要", "url": "原始链接"}},
    ...
  ]
}}
"""

        api_key = self.init_claude()
        if api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.content[0].text
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    data = json.loads(json_match.group())
                    return data.get("summaries", [])
            except Exception as e:
                print(f"[AI] Claude API调用失败: {e}")

        api_key = self.init_openai()
        if api_key:
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 3000
                    },
                    timeout=120
                )
                result = response.json()
                if "choices" in result:
                    text = result["choices"][0]["message"]["content"]
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        data = json.loads(json_match.group())
                        return data.get("summaries", [])
            except Exception as e:
                print(f"[AI] OpenAI API调用失败: {e}")

        return None

    def _local_summarize(self, news_list, region="global"):
        try:
            entity_kw = [
                'pfizer', 'moderna', 'biontech', 'astrazeneca', 'novartis', 'roche', 'merck',
                'gilead', 'eli lilly', 'johnson', 'abbvie', 'bms', 'sanofi', 'amgen',
                'regeneron', 'novavax', 'fda', 'ema', 'nmpa', 'who', 'cdc',
                '癌症', '肿瘤', '糖尿病', '阿尔茨海默', '帕金森', '心血管', '肥胖',
                '临床', '试验', '获批', '上市', '研发', '疫苗', '抗体', '基因疗法'
            ]

            scored_news = []
            for i, news in enumerate(news_list[:20]):
                title = news.get("title", "")
                snippet = news.get("snippet", "")[:300]
                url = news.get("url", "")
                text = (title + " " + snippet).lower()

                score = 1.0
                for kw in entity_kw:
                    if kw.lower() in text:
                        score += 2.0

                company_names = ['pfizer', 'moderna', 'biontech', 'astrazeneca', 'novartis',
                                'roche', 'merck', 'gilead', 'eli lilly', 'abbvie', 'sanofi']
                for co in company_names:
                    if co in text:
                        score += 3.0

                if any(x in text for x in ['fda', 'ema', 'nmpa', 'approval', 'approved', '获批']):
                    score += 4.0

                if any(x in text for x in ['clinical', 'trial', 'study', '试验', '临床']):
                    score += 2.0

                if any(x in text for x in ['funding', 'billion', 'million', 'acquisition',
                                           'merger', 'deal', '融资', '收购', '十亿', '百万']):
                    score += 3.0

                words = title.lower().split()
                title_score = len(set(words)) / max(len(words), 1)
                score += title_score * 2

                scored_news.append({
                    "news": news, "score": score, "title": title,
                    "snippet": snippet, "url": url
                })

            scored_news.sort(key=lambda x: x["score"], reverse=True)
            top10 = scored_news[:10]

            summaries = []
            for i, item in enumerate(top10, 1):
                news = item["news"]
                title = self._clean_html(news.get("title", ""))
                chinese_title = self._translate_to_chinese(title)
                if not chinese_title:
                    chinese_title = self._translate_title(title)

                snippet = self._clean_html(news.get("snippet", ""))[:200]
                chinese_snippet = self._translate_to_chinese(snippet) if snippet else ""
                if not chinese_snippet:
                    chinese_snippet = snippet[:100]

                summaries.append({
                    "index": i, "title": chinese_title,
                    "summary": chinese_snippet, "url": news.get("url", "")
                })

            print(f"[本地摘要] 为{region}生成{len(summaries)}条摘要")
            return summaries

        except Exception as e:
            print(f"[本地摘要] 生成失败: {e}")
            return None

    def _get_fallback_news(self):
        return [
            {"title": "Pfizer announces new cancer therapy results", "url": "https://pfizer.com",
             "snippet": "Pfizer reports positive Phase 3 trial data", "keyword": "Pfizer", "region": "Foreign"},
            {"title": "Moderna expands mRNA pipeline", "url": "https://modernatx.com",
             "snippet": "Moderna announces new pipeline developments", "keyword": "Moderna", "region": "Foreign"},
            {"title": "Chinese NMPA approves new diabetes drug", "url": "https://nmpa.gov.cn",
             "snippet": "China approves new GLP-1 treatment", "keyword": "NMPA", "region": "China"},
            {"title": "Roche Alzheimer drug shows promise", "url": "https://roche.com",
             "snippet": "Roche reports positive Alzheimer study", "keyword": "Roche", "region": "Foreign"},
            {"title": "AstraZeneca cancer drug approved in China", "url": "https://astrazeneca.com",
             "snippet": "AstraZeneca receives China approval", "keyword": "AstraZeneca", "region": "China"},
        ]

    def search_pharma_news(self):
        print("Starting Pharma/Biotech news fetch...")

        all_news = []

        foreign_rss = [
            ("https://www.biospace.com/rss/news/", "BioSpace", "Foreign"),
            ("https://www.fiercebiotech.com/rss/xml", "FierceBiotech", "Foreign"),
            ("https://www.fiercepharma.com/rss/xml", "FiercePharma", "Foreign"),
            ("https://www.evaluate.com/rss/vantage-news.xml", "Evaluate Vantage", "Foreign"),
            ("https://www.statnews.com/feed/", "STAT News", "Foreign"),
            ("https://feeds.bbci.co.uk/news/health/rss.xml", "BBC Health", "Foreign"),
        ]

        china_rss = [
            ("https://www.yigoonet.com/index.rss", "医药网", "China"),
            ("https://www.phirda.com/feed", "药时代", "China"),
            ("http://www.biodiscover.com/feed", "生物探索", "China"),
            ("https://www.chinastarmip.com/feed", "中国医疗器械", "China"),
        ]

        pharma_kw = [
            'pharma', 'biotech', 'biotechnology', 'pharmaceutical', 'biopharmaceutical',
            'vaccine', 'vaccination', 'drug', 'therapy', 'treatment', 'clinical',
            'cancer', 'tumor', 'oncology', 'diabetes', 'obesity', 'alzheimer', 'parkinson',
            'cardiovascular', 'immune', 'antibody', 'protein', 'mrna', 'crispr',
            'fda', 'ema', 'nmpa', 'approval', 'approved', 'pfizer', 'moderna', 'biontech',
            'astrazeneca', 'novartis', 'roche', 'merck', 'gilead', 'eli lilly',
            '医药', '制药', '生物制药', '疫苗', '癌症', '肿瘤', '糖尿病', '阿尔茨海默',
            '基因疗法', '细胞疗法', '抗体', '临床试验', '获批', '上市'
        ]

        print("\n=== Fetching Foreign Pharma Sources ===")
        for url, src, region in foreign_rss:
            try:
                print(f"[Get] {src}")
                resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text) if '<?xml' in resp.text[:50] else feedparser.parse(resp.content.decode('utf-8', errors='ignore'))
                    for ent in feed.entries[:15]:
                        title = ent.get('title', '')
                        summary = ent.get('summary', '') or ent.get('description', '') or ''
                        content = (title + ' ' + summary).lower()
                        if any(k.lower() in content for k in pharma_kw):
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
                print(f"  Error: {str(e)[:50]}")

        print("\n=== Fetching China Pharma Sources ===")
        for url, src, region in china_rss:
            try:
                print(f"[Get] {src}")
                resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content.decode('utf-8', errors='ignore'))
                    for ent in feed.entries[:10]:
                        title = ent.get('title', '')
                        summary = ent.get('summary', '') or ent.get('description', '') or ''
                        content = (title + ' ' + summary).lower()
                        if any(k.lower() in content for k in pharma_kw):
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
        print(f"\n[Total] {len(unique)} pharma news fetched")
        return unique

    def _categorize_news(self):
        cats = {
            "Cancer/Oncology": ["cancer", "tumor", "oncology", "CAR-T", "靶向", "肿瘤", "癌症"],
            "Vaccines": ["vaccine", "vaccination", "mrna", "疫苗", "接种"],
            "Metabolic/Diabetes": ["diabetes", "obesity", "glp-1", "糖尿病", "肥胖", "代谢"],
            "CNS/Neurology": ["alzheimer", "parkinson", "neuro", "阿尔茨海默", "帕金森", "神经"],
            "Immunology": ["immune", "antibody", "免疫", "抗体"],
            "Gene/Cell Therapy": ["gene therapy", "cell therapy", "crispr", "基因疗法", "细胞疗法"],
            "Regulatory/Approval": ["fda", "ema", "nmpa", "approval", "approved", "获批", "FDA", "EMA"],
            "Industry/Business": ["deal", "acquisition", "merger", "funding", "investment", "收购", "融资", "合作"],
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

        # 药研重点: high credibility sources
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
                <div style="background:white; border-left:3px solid #2e7d32; padding:12px 15px; margin-bottom:10px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                    <div style="font-weight:600; color:#222; margin-bottom:6px; font-size:14px; line-height:1.4;">
                        <span style="color:#ff9800;">{stars}</span> <a href="{url}" target="_blank" style="color:#1b5e20; text-decoration:none;">{title_cn}</a>
                    </div>
                    <div style="font-size:12px; color:#555; line-height:1.5; margin-bottom:6px;">{snippet}</div>
                    <div style="font-size:11px; color:#888;">
                        <span style="background:#e8f5e9; color:#2e7d32; padding:2px 6px; border-radius:3px;">{source}</span>
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
            return f'<li style="margin-bottom:8px; line-height:1.4;"><a href="{url}" target="_blank" style="color:#1b5e20; text-decoration:none;">{title_cn}</a><span style="color:#999; font-size:11px;">{time_str}</span></li>'

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
    <title>医药生物制药新闻日报 - {today}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; max-width:800px; margin:0 auto; padding:15px; background:#f5f5f5; }}
        .header {{ background:linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%); color:white; padding:20px 25px; border-radius:12px; margin-bottom:20px; box-shadow:0 4px 12px rgba(46,125,50,0.3); }}
        .header h1 {{ margin:0; font-size:22px; display:flex; align-items:center; gap:8px; }}
        .header .date {{ margin:8px 0 0 0; opacity:0.9; font-size:14px; }}
        .header .stats {{ display:flex; gap:10px; margin-top:12px; flex-wrap:wrap; }}
        .header .stats span {{ background:rgba(255,255,255,0.2); padding:5px 12px; border-radius:15px; font-size:12px; }}
        .section {{ background:white; border-radius:10px; padding:18px 20px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
        .section h2 {{ color:#333; font-size:15px; margin:0 0 12px 0; padding-bottom:8px; border-bottom:2px solid #eee; display:flex; align-items:center; gap:6px; }}
        .section h2 .count {{ font-size:12px; color:#999; font-weight:normal; margin-left:auto; }}
        .news-list {{ list-style:none; padding:0; margin:0; }}
        .footer {{ text-align:center; color:#bbb; margin-top:20px; font-size:11px; }}
        a {{ color:#1b5e20; text-decoration:none; }}
        a:hover {{ text-decoration:underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>💊 医药生物制药新闻日报 {today}</h1>
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
        <h2>🔥 药研重点 <span class="count">高可信度来源 ★★★★★</span></h2>
        {top_news_html}
    </div>

    <div class="section">
        <h2>🌍 国际动态 <span class="count">{intl_count}条</span></h2>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0 20px;">
            <ul class="news-list">{intl_html[:len(intl_html)//2] if intl_html else ''}</ul>
            <ul class="news-list">{intl_html[len(intl_html)//2:] if intl_html else ''}</ul>
        </div>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：STAT News / FiercePharma / BioSpace / Evaluate Vantage</div>
    </div>

    <div class="section">
        <h2>🇨🇳 中国动态 <span class="count">{china_count}条</span></h2>
        <ul class="news-list">{china_html if china_html else '<li style="color:#999;">暂无中国新闻</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：医药网 / 药时代 / 生物探索</div>
    </div>

    <div class="section">
        <h2>📈 行业快讯 <span class="count">{industry_count}条</span></h2>
        <ul class="news-list">{industry_html if industry_html else '<li style="color:#999;">暂无行业快讯</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">融资 / 并购 / 审批 / 临床试验 / 市场动态</div>
    </div>

    <div class="footer">
        <p>由 Pharma News Daily 自动生成 · {today}</p>
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
                subject = f"💊 医药新闻 日报 {today} ({count}条)"

            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = smtp_user
            msg['To'] = recipient

            plain_text = f"医药生物制药新闻日报 - {today}\n共 {count} 条\n\n请查看HTML版本获取完整内容。"
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

        html_path = os.path.join(day_folder, "pharma_news.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        json_path = os.path.join(day_folder, "pharma_news.json")
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
            self.search_pharma_news()
            folder = self.save_report(send_email=send_email)
            return 0
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(description="Pharma News Daily - 医药新闻日报")
    parser.add_argument("--config", default="config/pharma_config.json", help="Config path")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    parser.add_argument("--test", action="store_true", help="Test mode")

    args = parser.parse_args()

    news = PharmaNews(args.config)

    if args.test:
        print("Testing...")
        news.search_pharma_news()
    else:
        return news.run(send_email=not args.no_email)

    return 0


if __name__ == "__main__":
    sys.exit(main())
