#!/usr/bin/env python3
"""
Pharma News Daily - 医药与生物制药新闻收集
Daily pharma/biotech news collection and HTML report generation
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
    print("Error: Please install requests and feedparser")
    sys.exit(1)


class PharmaNews:
    def __init__(self, config_path="config/pharma_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.news_data = []
        self.summary = ""
        self.chinese_summary = ""
        self.ai_summaries = {"china": [], "global": []}

    def init_openai(self):
        """初始化OpenAI客户端"""
        api_key = self.config.get("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
        return api_key if api_key else None

    def init_claude(self):
        """初始化Claude客户端"""
        api_key = self.config.get("claude_api_key", os.environ.get("CLAUDE_API_KEY", ""))
        return api_key if api_key else None

    def _call_ai_summarize(self, news_list, region="global"):
        """调用AI生成中文摘要 - 优先使用本地摘要"""
        region_name = "国内" if region == "china" else "全球"
        region_label = "🇨🇳" if region == "china" else "🌍"

        # 首先尝试本地摘要算法（不需要API key）
        print(f"[摘要] 正在使用本地算法生成{region_name}新闻摘要...")
        local_result = self._local_summarize(news_list, region)
        if local_result:
            return local_result

        # 如果本地算法失败，再尝试外部API
        print(f"[摘要] 本地算法不可用，尝试外部AI API...")

        # 准备新闻列表
        news_text = ""
        for i, news in enumerate(news_list[:20], 1):  # 最多20条
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

        # 尝试Claude API
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
                import json
                import re
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    data = json.loads(json_match.group())
                    return data.get("summaries", [])
            except Exception as e:
                print(f"[AI] Claude API调用失败: {e}")

        # 尝试OpenAI API
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
                    import re
                    text = result["choices"][0]["message"]["content"]
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        data = json.loads(json_match.group())
                        return data.get("summaries", [])
            except Exception as e:
                print(f"[AI] OpenAI API调用失败: {e}")

        return None

    def _local_summarize(self, news_list, region="global"):
        """使用本地抽取式摘要算法生成中文摘要"""
        try:
            # 公司/机构名称关键词（用于计算重要性）
            entity_kw = [
                'pfizer', 'moderna', 'biontech', 'astrazeneca', 'novartis', 'roche', 'merck',
                'gilead', 'eli lilly', 'johnson', 'abbvie', 'bms', 'sanofi', 'amgen',
                'regeneron', 'novavax', 'fda', 'ema', 'nmpa', 'who', 'cdc',
                '癌症', '肿瘤', '糖尿病', '阿尔茨海默', '帕金森', '心血管', '肥胖',
                '临床', '试验', '获批', '上市', '研发', '疫苗', '抗体', '基因疗法'
            ]

            # 计算每条新闻的重要性得分
            scored_news = []
            for i, news in enumerate(news_list[:20]):
                title = news.get("title", "")
                snippet = news.get("snippet", "")[:300]
                url = news.get("url", "")
                text = (title + " " + snippet).lower()

                # 基础得分
                score = 1.0

                # 实体匹配加分
                for kw in entity_kw:
                    if kw.lower() in text:
                        score += 2.0

                # 公司名称出现
                company_names = ['pfizer', 'moderna', 'biontech', 'astrazeneca', 'novartis',
                                'roche', 'merck', 'gilead', 'eli lilly', 'abbvie', 'sanofi']
                for co in company_names:
                    if co in text:
                        score += 3.0

                # FDA/EMA/NMPA审批相关新闻加分
                if any(x in text for x in ['fda', 'ema', 'nmpa', 'approval', 'approved', '获批']):
                    score += 4.0

                # 临床试验相关
                if any(x in text for x in ['clinical', 'trial', 'study', '试验', '临床']):
                    score += 2.0

                # 融资/并购相关（业界重大新闻）
                if any(x in text for x in ['funding', 'billion', 'million', 'acquisition',
                                           'merger', 'deal', '融资', '收购', '十亿', '百万']):
                    score += 3.0

                # 计算标题中的关键词密度
                words = title.lower().split()
                title_score = len(set(words)) / max(len(words), 1)
                score += title_score * 2

                scored_news.append({
                    "news": news,
                    "score": score,
                    "title": title,
                    "snippet": snippet,
                    "url": url
                })

            # 按得分排序，取前10
            scored_news.sort(key=lambda x: x["score"], reverse=True)
            top10 = scored_news[:10]

            # 生成摘要
            summaries = []
            region_name = "国内" if region == "china" else "全球"
            for i, item in enumerate(top10, 1):
                news = item["news"]
                title = self._clean_html(news.get("title", ""))

                # 翻译标题
                chinese_title = self._translate_to_chinese(title)
                if not chinese_title:
                    chinese_title = self._translate_title(title)

                # 生成简短摘要（从snippet提取关键句子）
                snippet = self._clean_html(news.get("snippet", ""))[:200]
                chinese_snippet = self._translate_to_chinese(snippet) if snippet else ""
                if not chinese_snippet:
                    chinese_snippet = snippet[:100]

                summaries.append({
                    "index": i,
                    "title": chinese_title,
                    "summary": chinese_snippet,
                    "url": news.get("url", "")
                })

            print(f"[本地摘要] 为{region_name}生成{len(summaries)}条摘要")
            return summaries

        except Exception as e:
            print(f"[本地摘要] 生成失败: {e}")
            return None

    def _load_config(self):
        """Load config file"""
        config_file = os.path.join(os.path.dirname(__file__), "..", self.config_path)
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _clean_html(self, text):
        """Clean HTML tags"""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        return text.strip()

    def _translate_title(self, title):
        """Simple translation mapping for pharma terms"""
        trans = {
            "Pfizer": "[辉瑞]",
            "Moderna": "[莫德纳]",
            "BioNTech": "[BioNTech]",
            "AstraZeneca": "[阿斯利康]",
            "Novartis": "[诺华]",
            "Roche": "[罗氏]",
            "Merck": "[默克]",
            "Johnson & Johnson": "[强生]",
            "Eli Lilly": "[礼来]",
            "BMS": "[百时美施贵宝]",
            "AbbVie": "[艾伯维]",
            "Gilead": "[吉利德]",
            "Regeneron": "[再生元]",
            "Sanofi": "[赛诺菲]",
            "Amgen": "[安进]",
            "Novavax": "[诺瓦瓦克斯]",
            "FDA": "美国FDA",
            "EMA": "欧洲EMA",
            "China": "中国",
            "Chinese": "中国",
            "U.S.": "美国",
            "US": "美国",
            "UK": "英国",
            "EU": "欧盟",
            "vaccine": "疫苗",
            "vaccination": "疫苗接种",
            "drug": "药物",
            "therapy": "疗法",
            "treatment": "治疗",
            "clinical": "临床",
            "trial": "试验",
            "approval": "获批",
            "approved": "获批",
            "launch": "上市",
            "release": "发布",
            "announce": "宣布",
            "study": "研究",
            "research": "研究",
            "patient": "患者",
            "cancer": "癌症",
            "tumor": "肿瘤",
            "oncology": "肿瘤",
            "diabetes": "糖尿病",
            "obesity": "肥胖",
            "Alzheimer": "阿尔茨海默",
            "Parkinson": "帕金森",
            "cardiovascular": "心血管",
            "stroke": "中风",
            "immune": "免疫",
            "biotech": "生物技术",
            "biopharmaceutical": "生物制药",
            "pharmaceutical": "制药",
            "mRNA": "mRNA",
            "antibody": "抗体",
            "protein": "蛋白",
            "cell therapy": "细胞疗法",
            "gene therapy": "基因疗法",
            "CRISPR": "CRISPR",
            "deal": "合作",
            "acquisition": "收购",
            "merger": "合并",
            "funding": "融资",
            "investment": "投资",
            "partnership": "合作",
            "pipeline": "研发管线",
            "data": "数据",
            "results": "结果",
            "phase": "阶段",
            "FDA": "FDA",
            "EMA": "EMA",
            "NMPA": "国家药监局",
            "China": "中国",
            "global": "全球",
            "world": "世界",
            "million": "百万",
            "billion": "十亿",
        }
        result = title
        for k, v in trans.items():
            result = result.replace(k, v)
        result = result.replace(", ", " ").replace(".", "").replace("  ", " ")
        return result.strip()

    def _translate_to_chinese(self, text):
        """Use MyMemory free API to translate text to Chinese"""
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

    def _get_fallback_news(self):
        """Fallback news data"""
        return [
            {"title": "Pfizer announces new cancer therapy results", "url": "https://pfizer.com", "snippet": "Pfizer reports positive Phase 3 trial data", "keyword": "Pfizer", "region": "Foreign"},
            {"title": "Moderna expands mRNA pipeline", "url": "https://modernatx.com", "snippet": "Moderna announces new pipeline developments", "keyword": "Moderna", "region": "Foreign"},
            {"title": "Chinese NMPA approves new diabetes drug", "url": "https://nmpa.gov.cn", "snippet": "China approves new GLP-1 treatment", "keyword": "NMPA", "region": "China"},
            {"title": "Roche Alzheimer drug shows promise", "url": "https://roche.com", "snippet": "Roche reports positive Alzheimer study", "keyword": "Roche", "region": "Foreign"},
            {"title": "AstraZeneca cancer drug approved in China", "url": "https://astrazeneca.com", "snippet": "AstraZeneca receives China approval", "keyword": "AstraZeneca", "region": "China"},
        ]

    def search_pharma_news(self):
        """Search pharma/biotech news from RSS sources"""
        print("Starting Pharma/Biotech news fetch...")

        all_news = []

        # Foreign pharma RSS sources
        foreign_rss = [
            ("https://www.biospace.com/rss/news/", "BioSpace", "Foreign"),
            ("https://www.fiercebiotech.com/rss/xml", "FierceBiotech", "Foreign"),
            ("https://www.fiercepharma.com/rss/xml", "FiercePharma", "Foreign"),
            ("https://www.evaluate.com/rss/vantage-news.xml", "Evaluate Vantage", "Foreign"),
            ("https://www.statnews.com/feed/", "STAT News", "Foreign"),
            ("https://feeds.bbci.co.uk/news/health/rss.xml", "BBC Health", "Foreign"),
        ]

        # China pharma RSS sources
        china_rss = [
            ("https://www.yigoonet.com/index.rss", "医药网", "China"),
            ("https://www.phirda.com/feed", "药时代", "China"),
            ("http://www.biodiscover.com/feed", "生物探索", "China"),
            ("https://www.chinastarmip.com/feed", "中国医疗器械", "China"),
        ]

        # Pharma/biotech keywords
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

        # Fetch foreign news
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

        # Fetch China news
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
        print(f"\n[Total] {len(unique)} pharma news fetched")
        return unique

    def _categorize_news(self):
        """Categorize news by topic"""
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

    def _generate_summary(self):
        """Generate summary with Chinese highlights"""
        cats = self._categorize_news()
        cat_counts = {k: len(v) for k, v in cats.items()}
        sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)

        # Build category tags
        cat_html = ""
        for cat, cnt in sorted_cats:
            icon = {
                "Cancer/Oncology": "🧬",
                "Vaccines": "💉",
                "Metabolic/Diabetes": "🩺",
                "CNS/Neurology": "🧠",
                "Immunology": "🛡️",
                "Gene/Cell Therapy": "🔬",
                "Regulatory/Approval": "✅",
                "Industry/Business": "💰"
            }.get(cat, "📰")
            cat_html += f'<span class="cat-tag">{icon} {cat} ({cnt})</span>'

        self.summary = f'''
    <div class="summary-section">
        <h2>医药新闻要点</h2>
        <div class="category-tags">{cat_html}</div>
        <div class="highlight-list">
            {self._get_chinese_highlights()}
        </div>
    </div>'''

    def _get_chinese_highlights(self):
        """Get Chinese highlights - translate titles to Chinese"""
        highlights = ""

        for i, news in enumerate(self.news_data[:10], 1):
            title = news.get("title", "")
            snippet = news.get("snippet", "")[:200]
            url = news.get("url", "")
            pub = self._format_date(news.get("published", ""))
            src = news.get("keyword", "")
            region = news.get("region", "Foreign")

            # Translate title
            chinese_title = self._translate_to_chinese(title)
            if not chinese_title:
                chinese_title = self._translate_title(title)

            # Translate snippet
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
                        <span style="color: #2e7d32;">{region_label}</span>
                    </div>
                </div>
            </div>'''

        return highlights

    def _generate_top10_html(self, news_list, section_name, section_class):
        """Generate Top10 Chinese summary HTML"""
        items_html = ""
        for i, news in enumerate(news_list[:10], 1):
            title = news.get("title", "")
            snippet = news.get("snippet", "")[:100]
            url = news.get("url", "")

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
        """Generate China and Global Top10 summaries using AI"""
        china_news = [n for n in self.news_data if n.get("region") == "China"]
        global_news = [n for n in self.news_data if n.get("region") == "Foreign"]

        # Try to get AI-generated summaries
        if global_news:
            print("\n[AI] 正在生成全球医药新闻Top10摘要...")
            ai_summaries = self._call_ai_summarize(global_news, "global")
            if ai_summaries:
                self.ai_summaries["global"] = ai_summaries
            else:
                print("[AI] AI摘要生成失败，使用翻译模式")

        if china_news:
            print("[AI] 正在生成国内医药新闻Top10摘要...")
            ai_summaries = self._call_ai_summarize(china_news, "china")
            if ai_summaries:
                self.ai_summaries["china"] = ai_summaries
            else:
                print("[AI] AI摘要生成失败，使用翻译模式")

        # Generate HTML
        global_html = self._generate_ai_top10_html(self.ai_summaries.get("global", []), "🌍 全球医药新闻 Top 10", "top10-global") if self.ai_summaries.get("global") else ""
        china_html = self._generate_ai_top10_html(self.ai_summaries.get("china", []), "🇨🇳 国内医药新闻 Top 10", "top10-china") if self.ai_summaries.get("china") else ""

        # Fallback to translation if no AI summaries
        if not self.ai_summaries.get("global") and global_news:
            print("[Fallback] 使用翻译模式生成全球新闻Top10")
            global_html = self._generate_top10_html(global_news, "🌍 全球医药新闻 Top 10", "top10-global")
        if not self.ai_summaries.get("china") and china_news:
            print("[Fallback] 使用翻译模式生成国内新闻Top10")
            china_html = self._generate_top10_html(china_news, "🇨🇳 国内医药新闻 Top 10", "top10-china")

        return china_html + global_html

    def _generate_ai_top10_html(self, summaries, section_name, section_class):
        """Generate Top10 HTML using AI-generated summaries"""
        items_html = ""
        for i, item in enumerate(summaries[:10], 1):
            title = item.get("title", "")
            summary = item.get("summary", "")
            url = item.get("url", "")

            items_html += f'''
            <div class="top10-item">
                <span class="top10-num">{i}</span>
                <div class="top10-content">
                    <div class="top10-title"><a href="{url}" target="_blank">{title}</a></div>
                    <div class="top10-desc">{summary}</div>
                </div>
            </div>'''

        return f'''
    <div class="top10-section {section_class}">
        <h2>{section_name}</h2>
        <div class="top10-list">{items_html}
        </div>
    </div>'''

    def generate_html_report(self):
        """Generate HTML report"""
        today = datetime.now().strftime("%Y-%m-%d")

        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>医药生物制药新闻 - {date}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #2e7d32 0%, #00acc1 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .top10-section {{ background: white; padding: 25px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .top10-section h2 {{ margin: 0 0 15px 0; color: #1a1a1a; font-size: 20px; padding-bottom: 10px; border-bottom: 2px solid #2e7d32; }}
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
        .top10-title a:hover {{ color: #2e7d32; }}
        .top10-desc {{ font-size: 13px; color: #666; line-height: 1.4; margin-top: 4px; }}
        .summary-section {{ background: white; padding: 25px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .summary-section h2 {{ margin: 0 0 20px 0; color: #1a1a1a; font-size: 20px; padding-bottom: 15px; border-bottom: 2px solid #2e7d32; }}
        .category-tags {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
        .cat-tag {{ background: linear-gradient(135deg, #2e7d32 0%, #00acc1 100%); color: white; padding: 8px 16px; border-radius: 20px; font-size: 14px; }}
        .highlight-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .highlight-item {{ display: flex; align-items: flex-start; gap: 12px; padding: 15px; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #2e7d32; }}
        .highlight-num {{ background: #2e7d32; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: bold; flex-shrink: 0; }}
        .highlight-content {{ flex: 1; }}
        .highlight-title {{ font-size: 16px; font-weight: 600; color: #333; line-height: 1.5; margin-bottom: 5px; }}
        .highlight-title a {{ color: #333; text-decoration: none; }}
        .highlight-title a:hover {{ color: #2e7d32; }}
        .highlight-snippet {{ font-size: 13px; color: #666; line-height: 1.5; margin: 5px 0; }}
        .highlight-meta {{ font-size: 13px; color: #888; }}
        .news-item {{ background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .news-date {{ color: #999; font-size: 12px; margin-bottom: 5px; }}
        .news-item h3 {{ margin: 0 0 10px 0; color: #333; }}
        .news-item a {{ color: #2e7d32; text-decoration: none; }}
        .snippet {{ color: #666; font-size: 14px; line-height: 1.6; }}
        .tag {{ display: inline-block; background: #e8f4f8; color: #2a7bb0; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 8px; }}
        .tag-china {{ background: #ffeaea; color: #d32f2f; }}
        .tag-foreign {{ background: #e3f2fd; color: #1976d2; }}
        .news-meta {{ margin-top: 10px; display: flex; align-items: center; flex-wrap: wrap; gap: 5px; }}
        .section-title {{ font-size: 16px; font-weight: bold; color: #333; margin: 20px 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #2e7d32; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>医药生物制药新闻</h1>
        <p>{date} | {count} 篇文章</p>
    </div>

    {chinese_top10}

    {summary}

    <div class="section-title">[全部新闻]</div>
    {news_html}
    <div class="footer">
        Generated by Pharma News Assistant
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
            chinese_top10=self.chinese_summary
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
            print("[Email] Email sending is disabled (enable_email=false)")
            return True

        if not smtp_user or not smtp_password or not recipient:
            print("[Email] Email config incomplete, skip sending")
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"医药生物制药新闻 - {today}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = smtp_user
        msg['To'] = recipient

        plain_text = f"医药生物制药新闻 - {today}\n\n请查看HTML版本获取完整内容。"
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

        # Generate Chinese Top10 summary
        self.chinese_summary = self._generate_chinese_top10_html()

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

        # Send email
        self._send_email(html_content)

        return day_folder

    def run(self):
        """Run pharma news collection"""
        try:
            self.search_pharma_news()
            folder = self.save_report()
            return 0
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(description="Pharma News Daily")
    parser.add_argument("--config", default="config/pharma_config.json", help="Config path")
    parser.add_argument("--test", action="store_true", help="Test mode")

    args = parser.parse_args()

    news = PharmaNews(args.config)

    if args.test:
        print("Testing...")
        news.search_pharma_news()
    else:
        return news.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
