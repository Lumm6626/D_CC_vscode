#!/usr/bin/env python3
"""
Allergy Clinics News Daily Report - 过敏诊所新闻日报
功能：从news-daily、pharma-news、medical-device-news三个数据源收集新闻
      按地区分类，高亮标注过敏相关内容，生成HTML邮件日报
"""

import json
import os
import sys
import ssl
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


class AllergyNewsDaily:
    """过敏诊所新闻日报生成器"""

    # 过敏相关关键词（更精准）
    ALLERGY_KEYWORDS = [
        # 英文核心关键词
        'allergy', 'allergic', 'allergen', 'allergen immunotherapy',
        'allergic disease', 'allergic rhinitis', 'allergic asthma',
        'atopic dermatitis', 'atopic', 'atopy',
        'food allergy', 'peanut allergy', 'drug allergy', 'latex allergy',
        'dust mite allergy', 'pollen allergy', 'hay fever',
        'anaphylaxis', 'anaphylactic', 'anaphylatoxin',
        'urticaria', 'hives', 'angioedema',
        'immunoglobulin e', 'ige antibody', 'ige level',
        'skin prick test', 'patch test', 'allergy test',
        'sublingual immunotherapy', 'SLIT', 'SCIT',
        'epinephrine auto-injector', 'epi pen', 'adrenaline',
        'antihistamine', 'corticosteroid', 'mast cell stabilizer',
        'allergist', 'clinical immunology', 'immunologist',
        'mastocytosis', 'eosinophilic esophagitis',
        # 中文关键词
        '过敏', '变态反应', '脱敏治疗', '特异性免疫治疗',
        '过敏性鼻炎', '过敏性哮喘', '过敏性皮炎', '过敏原',
        '湿疹', '荨麻疹', '血管性水肿', '食物过敏',
        '药物过敏', '花粉过敏', '尘螨过敏',
        '组胺', '抗组胺', '肾上腺素', 'ige',
        '舌下免疫治疗', '皮下免疫治疗'
    ]

    # 来源可信度权重（用于美国优先排序）
    SOURCE_CREDIBILITY = {
        # 美国权威过敏专业来源 - 最高权重
        'AAAAI': 100, 'ACAAI': 100, 'Allergy & Asthma Network': 100,
        'American College of Allergy, Asthma & Immunology': 100,
        'American Academy of Allergy, Asthma & Immunology': 100,
        # 美国行业媒体
        'Fierce Healthcare': 80, 'Fierce Pharma': 80, 'Fierce Biotech': 80,
        'Fierce MedTech': 80, 'Endpoints News': 80,
        'Modern Healthcare': 75, 'Beckers Hospital Review': 70,
        'Reuters Health': 70, 'STAT News': 70,
        'Medscape Allergy': 90,
        # 欧洲过敏专业来源
        'EAACI': 95, 'BSACI': 90, 'DGAKI': 85,
        # 亚太过敏专业来源
        'ASCIA': 85, 'AusDoc': 70, 'Medical Republic': 70,
        'NewsGP': 70, 'RACGP': 70, 'National Allergy Council': 80,
        # 行业快讯来源
        'PitchBook': 60, 'Crunchbase': 60, 'MedTech Dive': 65,
        'AACC Clinical Lab News': 65, 'ClinicalTrials.gov': 70,
        # 其他通用来源
        'NYTimes': 50, 'BBC': 50, 'Reuters': 50
    }

    # 美国来源关键词
    US_SOURCE_KEYWORDS = ['AAAAI', 'ACAAI', 'Allergy & Asthma Network', 'Fierce',
                          'Endpoints', 'Modern Healthcare', 'STAT', 'Beckers',
                          'Medscape', 'American College', 'American Academy']

    # 欧洲来源关键词
    EU_SOURCE_KEYWORDS = ['EAACI', 'BSACI', 'DGAKI', 'European', 'UK', 'Britain', 'EMA']

    # 亚太来源关键词
    APAC_SOURCE_KEYWORDS = ['ASCIA', 'AusDoc', 'Medical Republic', 'NewsGP', 'RACGP',
                            'National Allergy Council', 'Japan', 'Korea', 'Australia']

    # 行业快讯关键词（并购/融资/临床试验）
    INDUSTRY_KEYWORDS = ['acquisition', 'merger', 'acquire', 'merge',
                         'funding', 'investment', ' Series ', 'IPO', 'M&A',
                         'clinical trial', 'phase 1', 'phase 2', 'phase 3',
                         'FDA approval', 'EMA approval', 'regulatory',
                         'launch', 'pipeline', 'deal', 'partnership']

    # 标题翻译映射表
    TITLE_TRANSLATION = {
        # 过敏相关
        'anaphylaxis': '过敏性休克', 'anaphylactic': '过敏性休克',
        'allergy': '过敏', 'allergic': '过敏性', 'allergen': '过敏原',
        'allergic rhinitis': '过敏性鼻炎', 'allergic asthma': '过敏性哮喘',
        'atopic dermatitis': '特应性皮炎', 'eczema': '湿疹',
        'urticaria': '荨麻疹', 'hives': '荨麻疹',
        'angioedema': '血管性水肿',
        'food allergy': '食物过敏', 'peanut allergy': '花生过敏',
        'drug allergy': '药物过敏', 'latex allergy': '乳胶过敏',
        'pollen allergy': '花粉过敏', 'dust mite': '尘螨',
        'hay fever': '花粉热', 'hayfever': '花粉热',
        'immunotherapy': '免疫治疗', 'AIT': '特异性免疫治疗',
        'SLIT': '舌下免疫治疗', 'SCIT': '皮下免疫治疗',
        'sublingual': '舌下', 'subcutaneous': '皮下',
        'epinephrine': '肾上腺素', 'adrenaline': '肾上腺素',
        'epi pen': '肾上腺素笔', 'auto-injector': '自动注射器',
        'antihistamine': '抗组胺药', 'corticosteroid': '皮质类固醇',
        'mast cell': '肥大细胞', 'ige': 'IgE',
        'skin prick test': '皮肤点刺试验', 'patch test': '斑贴试验',
        'allergist': '过敏科医生', 'immunologist': '免疫科医生',
        'asthma': '哮喘', 'rhinitis': '鼻炎', 'sinusitis': '鼻窦炎',
        'eosinophilic esophagitis': '嗜酸性食管炎', 'EoE': '嗜酸性食管炎',
        'mastocytosis': '肥大细胞增多症',
        # 学校相关
        'school': '学校', 'schools': '学校', 'children': '儿童', 'kids': '儿童',
        'student': '学生', 'students': '学生',
        # 行动呼吁
        'call for urgent action': '呼吁紧急行动', 'urgent action': '紧急行动',
        'calls for': '呼吁', 'advocates': '倡导',
        # 地区/机构
        'EAACI': '欧洲过敏与临床免疫学会', 'BSACI': '英国过敏与临床免疫学会',
        'DGAKI': '德国过敏与临床免疫学会', 'AAAAI': '美国过敏与临床免疫学会',
        'ACAAI': '美国过敏哮喘与免疫学委员会', 'ASCIA': '澳大利亚临床免疫学学会',
        # 行业快讯
        'FDA': '美国食品药品监管局', 'CDC': '美国疾病控制中心', 'NIH': '美国国立卫生研究院',
        'EMA': '欧洲药品管理局', 'NHS': '英国国家医疗服务体系',
        # 关键词
        'treatment': '治疗', 'therapy': '治疗', 'diagnostic': '诊断',
        'prevalence': '患病率', 'incidence': '发病率', 'burden': '负担',
        'guideline': '指南', 'recommendation': '推荐', 'consensus': '共识',
        'patient': '患者', 'population': '人群', 'study': '研究',
        'clinical': '临床', 'trial': '试验', 'patient': '患者',
        'safety': '安全性', 'efficacy': '有效性', 'outcome': '结局',
        'risk': '风险', 'benefit': '获益', 'management': '管理',
        'prevention': '预防', 'care': '护理', 'awareness': '关注',
        'documentary': '纪录片', 'podcast': '播客', 'campaign': '活动',
        'awareness day': '关注日', 'global': '全球', 'international': '国际'
    }

    # 地区分类关键词
    REGION_KEYWORDS = {
        '美国': ['USA', 'United States', 'America', 'FDA', 'CDC', 'NIH', 'US ', 'U.S.'],
        '欧洲': ['EU', 'European', 'UK', 'Britain', 'Germany', 'France', 'Italy', 'Spain', 'EMA'],
        '中国': ['China', 'Chinese', 'Hong Kong', 'Taiwan', 'Macau', 'Beijing', 'Shanghai', 'Shenzhen'],
        '亚太其他': ['Japan', 'Korea', 'Australia', 'India', 'Singapore', 'Thailand', 'Indonesia', 'Malaysia']
    }

    def __init__(self, base_path=None, config_path="config/email_config.json"):
        # base_path 应该是 agents 目录
        if base_path is None:
            # server.py 在 agents/news/allergy-news-daily/ 下，向上两级到 agents/
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # current_dir = agents/news/allergy-news-daily, parent = agents/news, grandparent = agents
            self.base_path = os.path.dirname(os.path.dirname(current_dir))
        else:
            self.base_path = base_path
        self.config_path = os.path.join(self.base_path, config_path)
        self.news_data = {
            'allergy-sources': [],  # 主要过敏专业新闻源
            'news-daily': [],
            'pharma-news': [],
            'medical-device-news': []
        }
        self.all_news = []
        self.regions = {
            '美国': [],
            '欧洲': [],
            '中国': [],
            '其他亚太': []
        }
        self.allergy_news = []
        self.stats = {}

    def _load_config(self):
        """加载邮件配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _is_allergy_related(self, title, snippet):
        """判断是否与过敏相关"""
        content = (title + ' ' + snippet).lower()
        # 移除HTML标签和URLs以避免误匹配
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'http\S+|www\.\S+', '', content)

        # 使用单词边界匹配敏感词
        def has_word(text, word):
            """检查单词是否作为独立词出现"""
            pattern = r'\b' + re.escape(word) + r'\b'
            return bool(re.search(pattern, text, re.IGNORECASE))

        # 核心过敏关键词
        core_terms = [
            'allergy', 'allergen',
            'anaphylaxis', 'anaphylactic',
            'urticaria', 'hives',
            'angioedema',
            'atopic', 'atopy',
            'eczema',
            'hay fever',
            'epinephrine', 'adrenaline',
            'antihistamine',
            'SLIT', 'SCIT',
            'mastocytosis',
            'allergist', 'immunologist',
            # 中文
            '过敏', '变态反应', '脱敏', '过敏原',
            '荨麻疹', '血管性水肿', '湿疹'
        ]

        for term in core_terms:
            if has_word(content, term):
                return True

        # 需要上下文的次级关键词
        context_terms = {
            'immunotherapy': ['allergen', 'allergy', 'allergic', 'AIT'],
            'asthma': ['allergic', 'atopic', 'allergen', 'respiratory'],
            'rhinitis': ['allergic', 'hay fever', 'allergen', 'nasal'],
            'dermatitis': ['atopic', 'allergic', 'contact', 'eczema'],
            'sinusitis': ['allergic', 'rhinitis'],
            'ige': ['immunoglobulin', 'antibody', 'allergy', 'allergic'],
            'immunoglobulin': ['ige', 'allergy', 'allergic', 'antibody'],
            '肾上腺素': ['过敏', '变态反应', '急救'],
            '哮喘': ['过敏', '变态反应', '呼吸'],
            '鼻炎': ['过敏', '变态反应', '鼻']
        }

        for keyword, contexts in context_terms.items():
            if has_word(content, keyword):
                for ctx in contexts:
                    if ctx in content:
                        return True

        # 复合词组检查
        compound_phrases = [
            'allergic disease', 'allergic reaction', 'allergic response',
            'allergic rhinitis', 'allergic asthma', 'allergic dermatitis',
            'food allergy', 'peanut allergy', 'drug allergy', 'latex allergy',
            'pollen allergy', 'dust mite allergy',
            'skin prick test', 'patch test', 'allergy test',
            '过敏性鼻炎', '过敏性哮喘', '过敏性皮炎',
            '食物过敏', '药物过敏', '花粉过敏', '尘螨过敏'
        ]

        for phrase in compound_phrases:
            if phrase in content:
                return True

        return False

    def _classify_region(self, title, snippet, region_tag):
        """分类地区"""
        content = (title + ' ' + snippet).lower()

        # 先检查是否有明确的地区标签
        if region_tag == 'China':
            return '中国'

        # 检查关键词
        for region, keywords in self.REGION_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content:
                    return region

        return '美国'  # 默认归类到美国（最常见的新闻来源）

    def _clean_title(self, title):
        """清理标题噪音：去除 'Read more'、日期前缀、浏览量等"""
        if not title:
            return ''
        # 移除HTML标签
        title = re.sub(r'<[^>]+>', '', title)
        # 移除 Read more 和类似链接文本
        title = re.sub(r'\s*[-|]*\s*Read more\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*[-|]*\s*Read\s*more\s*at[^\s]*\s*', '', title, flags=re.IGNORECASE)
        # 移除日期前缀格式: "27 Apr 2026 395 views"
        title = re.sub(r'^\d{1,2}\s+\w+\s+\d{4}\s+\d+\s+views\s*', '', title)
        title = re.sub(r'^\d{4}-\d{2}-\d{2}\s*', '', title)
        title = re.sub(r'^\w+\s+\d{1,2},?\s+\d{4}\s*', '', title)
        # 移除浏览量后缀
        title = re.sub(r'\s*\d+\s*views?\s*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\|\s*\d+\s*$', '', title)
        # 清理多余空格
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    def _translate_title(self, title):
        """翻译标题为中文"""
        if not title:
            return ''
        result = title
        # 按长度降序排列，确保长词组优先匹配
        sorted_translations = sorted(self.TITLE_TRANSLATION.items(),
                                    key=lambda x: len(x[0]), reverse=True)
        for eng, chn in sorted_translations:
            result = re.sub(r'\b' + re.escape(eng) + r'\b', chn, result, flags=re.IGNORECASE)
        return result

    def _get_source_region(self, keyword):
        """根据来源判断地区"""
        source_str = (keyword or '').lower()
        for kw in self.US_SOURCE_KEYWORDS:
            if kw.lower() in source_str:
                return '美国'
        for kw in self.EU_SOURCE_KEYWORDS:
            if kw.lower() in source_str:
                return '欧洲'
        for kw in self.APAC_SOURCE_KEYWORDS:
            if kw.lower() in source_str:
                return '亚太'
        return '美国'  # 默认美国

    def _calculate_priority(self, news_item):
        """计算新闻优先级：来源可信度(40%) + 地区权重(30%) + 时效性(30%)"""
        keyword = news_item.get('keyword', '')
        source_type = news_item.get('source_type', '')

        # 来源可信度 (0-100)
        credibility = self.SOURCE_CREDIBILITY.get(keyword, 50)

        # 地区权重
        region = news_item.get('region', '美国')
        region_weight = {'美国': 100, '欧洲': 70, '亚太': 60, '中国': 60}.get(region, 50)

        # 时效性 (0-100，越新鲜越高)
        recency_score = 50  # 默认中等
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

        # 综合优先级
        priority = (credibility * 0.4) + (region_weight * 0.3) + (recency_score * 0.3)
        return priority

    def _is_industry_news(self, title, snippet):
        """判断是否是行业快讯（并购/融资/临床试验）"""
        content = (title + ' ' + snippet).lower()
        for kw in self.INDUSTRY_KEYWORDS:
            if kw.lower() in content:
                return True
        return False

    def _format_time_ago(self, published):
        """格式化时间显示为'X小时前'"""
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

    def _load_news_file(self, folder, date_str):
        """加载单个新闻文件"""
        # 文件夹映射：逻辑名称 -> 实际相对路径（相对于 base_path=agents/）
        folder_mapping = {
            'allergy-sources': 'news/allergy-news-daily',
            'news-daily': 'news/ai-news',
            'pharma-news': 'news/pharma-news',
            'medical-device-news': 'news/medical-device-news'
        }

        actual_folder = folder_mapping.get(folder, folder)
        file_path = os.path.join(self.base_path, actual_folder, 'output', date_str)
        possible_names = {
            'allergy-sources': ['allergy_news.json'],
            'news-daily': ['news.json', 'ai_news.json'],
            'pharma-news': ['pharma_news.json'],
            'medical-device-news': ['news.json', 'medical_news.json']
        }

        for name in possible_names.get(folder, ['news.json']):
            full_path = os.path.join(file_path, name)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return data.get('news', [])
                except Exception as e:
                    print(f"  [Error] Loading {folder}: {e}")
        return []

    def load_all_news(self, date_str=None):
        """加载所有新闻数据"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 用于URL去重
        seen_urls = set()

        # 优先加载过敏专业新闻源
        folders = ['allergy-sources', 'news-daily', 'pharma-news', 'medical-device-news']

        for folder in folders:
            news_list = self._load_news_file(folder, date_str)
            print(f"  [Loaded] {folder}: {len(news_list)} articles")
            self.news_data[folder] = news_list

            for item in news_list:
                # URL去重
                url = item.get('url', '')
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)

                item['source'] = folder

                # 过敏专业新闻源的文章直接标记为过敏相关
                if folder == 'allergy-sources':
                    item['is_allergy'] = True
                else:
                    # 其他来源需要判断是否过敏相关
                    item['is_allergy'] = self._is_allergy_related(
                        item.get('title', ''),
                        item.get('snippet', '')
                    )

                # 分类地区
                item['region'] = self._classify_region(
                    item.get('title', ''),
                    item.get('snippet', ''),
                    item.get('region', '')
                )
                self.all_news.append(item)

        # 统计
        self.allergy_news = [n for n in self.all_news if n['is_allergy']]
        for region in self.regions:
            self.regions[region] = [n for n in self.all_news if n['region'] == region]

        self.stats = {
            'total': len(self.all_news),
            'allergy': len(self.allergy_news),
            'by_region': {r: len(self.regions[r]) for r in self.regions},
            'by_source': {s: len(self.news_data[s]) for s in self.news_data}
        }

        return self.stats

    def _format_snippet(self, snippet, max_len=150):
        """格式化摘要"""
        if not snippet:
            return ''
        # 移除HTML标签
        snippet = re.sub(r'<[^>]+>', '', snippet)
        snippet = snippet.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        if len(snippet) > max_len:
            snippet = snippet[:max_len] + '...'
        return snippet

    def _generate_html_report(self, date_str=None):
        """生成HTML日报 - 美国优先排序版本"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        today_formatted = datetime.now().strftime("%Y年%m月%d日")

        # 分离地区数据
        us_news = self.regions.get('美国', [])
        eu_news = self.regions.get('欧洲', [])
        apac_news = self.regions.get('亚太', []) + self.regions.get('其他亚太', [])
        china_news = self.regions.get('中国', [])

        # 美国新闻按优先级排序
        us_news_sorted = sorted(us_news, key=self._calculate_priority, reverse=True)
        eu_news_sorted = sorted(eu_news, key=self._calculate_priority, reverse=True)
        apac_news_sorted = sorted(apac_news, key=self._calculate_priority, reverse=True)

        # 找出行业快讯（从所有新闻中筛选）
        industry_news = [n for n in self.all_news if self._is_industry_news(
            n.get('title', ''), n.get('snippet', ''))]
        industry_news_sorted = sorted(industry_news, key=self._calculate_priority, reverse=True)

        # 今日重点：美国权威来源新闻（限10条，可信度90+）
        top_us = [n for n in us_news_sorted if self.SOURCE_CREDIBILITY.get(n.get('keyword', ''), 0) >= 90][:10]

        def render_news_card(n, show_stars=True):
            """渲染单条新闻卡片"""
            title = self._clean_title(n.get('title', ''))
            title_cn = self._translate_title(title)
            snippet = self._format_snippet(n.get('snippet', ''), 120)
            url = n.get('url', '#')
            source = n.get('keyword', '')
            region = n.get('region', '')
            time_ago = self._format_time_ago(n.get('published', ''))
            credibility = self.SOURCE_CREDIBILITY.get(source, 50)
            stars = '★' * min(5, max(1, credibility // 20)) if show_stars else ''

            region_flag = {"美国": "🇺🇸", "欧洲": "🇪🇺", "中国": "🇨🇳", "亚太": "🌏"}.get(region, "🌏")
            time_str = f" · {time_ago}" if time_ago else ""

            return f'''
                <div style="background:white; border-left:3px solid #ff5722; padding:12px 15px; margin-bottom:10px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
                    <div style="font-weight:600; color:#222; margin-bottom:6px; font-size:14px; line-height:1.4;">
                        {'<span style="color:#ff9800;">' + stars + '</span> ' if show_stars and stars else ''}<a href="{url}" target="_blank" style="color:#d84315; text-decoration:none;">{title_cn}</a>
                    </div>
                    <div style="font-size:12px; color:#555; line-height:1.5; margin-bottom:6px;">{snippet}</div>
                    <div style="font-size:11px; color:#888;">
                        <span style="background:#e3f2fd; color:#1565c0; padding:2px 6px; border-radius:3px;">{source}</span>
                        <span style="margin-left:8px;">{region_flag} {region}{time_str}</span>
                    </div>
                </div>'''

        def render_simple_news_item(n):
            """渲染简洁新闻条目"""
            title = self._clean_title(n.get('title', ''))
            title_cn = self._translate_title(title)
            url = n.get('url', '#')
            source = n.get('keyword', '')
            time_ago = self._format_time_ago(n.get('published', ''))
            time_str = f" · {time_ago}" if time_ago else ""
            return f'<li style="margin-bottom:8px; line-height:1.4;"><a href="{url}" target="_blank" style="color:#1976d2; text-decoration:none;">{title_cn}</a><span style="color:#999; font-size:11px;">{time_str}</span></li>'

        # 今日重点HTML
        top_news_html = ''
        if top_us:
            for n in top_us:
                top_news_html += render_news_card(n, show_stars=True)

        # 美国动态HTML
        us_other = us_news_sorted[10:35] if len(us_news_sorted) > 10 else us_news_sorted[1:]
        us_other_html = ''.join([render_simple_news_item(n) for n in us_other[:25]])

        # 欧洲动态HTML
        eu_html = ''.join([render_simple_news_item(n) for n in eu_news_sorted[:20]])

        # 亚太动态HTML
        apac_html = ''.join([render_simple_news_item(n) for n in apac_news_sorted[:15]])

        # 行业快讯HTML
        industry_html = ''.join([render_simple_news_item(n) for n in industry_news_sorted[:10]])

        # 统计概览
        us_count = len(us_news)
        eu_count = len(eu_news)
        apac_count = len(apac_news)
        industry_count = len(industry_news)

        html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>过敏新闻日报 - {date_str}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; max-width:800px; margin:0 auto; padding:15px; background:#f5f5f5; }}
        .header {{ background:linear-gradient(135deg, #e64a19 0%, #d84315 100%); color:white; padding:20px 25px; border-radius:12px; margin-bottom:20px; box-shadow:0 4px 12px rgba(211,47,47,0.3); }}
        .header h1 {{ margin:0; font-size:22px; display:flex; align-items:center; gap:8px; }}
        .header .date {{ margin:8px 0 0 0; opacity:0.9; font-size:14px; }}
        .header .stats {{ display:flex; gap:10px; margin-top:12px; flex-wrap:wrap; }}
        .header .stats span {{ background:rgba(255,255,255,0.2); padding:5px 12px; border-radius:15px; font-size:12px; }}
        .section {{ background:white; border-radius:10px; padding:18px 20px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
        .section h2 {{ color:#333; font-size:15px; margin:0 0 12px 0; padding-bottom:8px; border-bottom:2px solid #eee; display:flex; align-items:center; gap:6px; }}
        .section h2 .count {{ font-size:12px; color:#999; font-weight:normal; margin-left:auto; }}
        .news-list {{ list-style:none; padding:0; margin:0; }}
        .highlight-card {{ background:white; border-left:4px solid #ff5722; padding:14px 16px; margin-bottom:12px; border-radius:6px; box-shadow:0 2px 6px rgba(0,0,0,0.08); }}
        .highlight-card h3 {{ margin:0 0 8px 0; font-size:14px; color:#222; }}
        .highlight-card .meta {{ font-size:11px; color:#888; margin-top:6px; }}
        .footer {{ text-align:center; color:#bbb; margin-top:20px; font-size:11px; }}
        a {{ color:#1976d2; text-decoration:none; }}
        a:hover {{ text-decoration:underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📅 过敏新闻日报 {date_str}</h1>
        <p class="date">{today_formatted}</p>
        <div class="stats">
            <span>共 {self.stats['total']} 条</span>
            <span>🇺🇸 美国 {us_count}条</span>
            <span>🇪🇺 欧洲 {eu_count}条</span>
            <span>🌏 亚太 {apac_count}条</span>
            <span>📈 行业 {industry_count}条</span>
        </div>
    </div>

    <div class="section">
        <h2>🔥 今日重点 <span class="count">美国权威来源 ★★★★★</span></h2>
        {top_news_html if top_news_html else '<div style="color:#999; padding:20px; text-align:center;">暂无重点新闻</div>'}
    </div>

    <div class="section">
        <h2>🌍 美国动态 <span class="count">{us_count}条</span></h2>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0 20px;">
            <ul class="news-list">{us_other_html[:len(us_other_html)//2] if us_other_html else ''}</ul>
            <ul class="news-list">{us_other_html[len(us_other_html)//2:] if us_other_html else ''}</ul>
        </div>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：AAAAI / ACAAI / Allergy & Asthma Network / Becker's / Medscape</div>
    </div>

    <div class="section">
        <h2>🌍 欧洲动态 <span class="count">{eu_count}条</span></h2>
        <ul class="news-list">{eu_html if eu_html else '<li style="color:#999;">暂无欧洲新闻</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：EAACI / BSACI / DGAKI</div>
    </div>

    <div class="section">
        <h2>🌏 亚太动态 <span class="count">{apac_count}条</span></h2>
        <ul class="news-list">{apac_html if apac_html else '<li style="color:#999;">暂无亚太新闻</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：ASCIA / RACGP / NewsGP / AusDoc</div>
    </div>

    <div class="section">
        <h2>📈 行业快讯 <span class="count">{industry_count}条</span></h2>
        <ul class="news-list">{industry_html if industry_html else '<li style="color:#999;">暂无行业快讯</li>'}</ul>
        <div style="color:#999; font-size:11px; margin-top:10px;">来源：Fierce / Endpoints / PitchBook / Crunchbase</div>
    </div>

    <div class="footer">
        <p>由 Allergy News Daily 自动生成 · {date_str}</p>
    </div>
</body>
</html>'''

        return html_template

    def _send_email(self, html_content, config):
        """发送邮件"""
        smtp_server = config.get("smtp_server", "smtp.163.com")
        smtp_port = 465
        smtp_user = config.get("email", "")
        smtp_password = config.get("password", "")
        recipient = config.get("email", "")

        if not smtp_user or not smtp_password:
            print("[Email] 邮件配置不完整，跳过发送")
            return False

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            subject = f"🏥 Allergy Clinics 日报 {today} ({self.stats['allergy']}条过敏相关)"

            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = smtp_user
            msg['To'] = recipient

            plain_text = self._generate_plain_text()
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

    def _generate_plain_text(self):
        """生成纯文本版本"""
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            f"Allergy Clinics 行业日报 - {today}",
            "=" * 50,
            f"共 {self.stats['total']} 条新闻，其中 {self.stats['allergy']} 条与过敏相关",
            "",
            "【过敏相关重点】"
        ]

        for n in self.allergy_news[:5]:
            title = re.sub(r'<[^>]+>', '', n.get('title', ''))
            lines.append(f"• {title}")

        lines.append("")
        lines.append("【地区分布】")
        for region, count in self.stats['by_region'].items():
            lines.append(f"  {region}: {count}条")

        return "\n".join(lines)

    def save_report(self, date_str=None, send_email=True):
        """保存日报"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 输出到当前 agent 的 output 目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_folder = os.path.join(current_dir, 'output')
        os.makedirs(output_folder, exist_ok=True)

        html_content = self._generate_html_report(date_str)

        # 保存HTML
        html_path = os.path.join(output_folder, f"allergy_daily_{date_str}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"[保存] 日报已保存至: {html_path}")

        # 发送邮件
        if send_email:
            config = self._load_config()
            self._send_email(html_content, config)

        return html_path

    def generate(self, date_str=None, send_email=True):
        """生成日报主流程"""
        print(f"[Allergy News Daily] 开始生成 {date_str or '今日'} 日报...")

        # 加载新闻
        self.load_all_news(date_str)

        # 输出统计
        print(f"[统计] 共加载 {self.stats['total']} 条新闻")
        print(f"[统计] 过敏相关: {self.stats['allergy']} 条")
        print(f"[统计] 地区分布: {self.stats['by_region']}")

        # 保存并发送
        path = self.save_report(date_str, send_email)

        return {
            'stats': self.stats,
            'report_path': path
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Allergy Clinics 新闻日报生成器")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)", default=None)
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    args = parser.parse_args()

    report = AllergyNewsDaily()
    result = report.generate(args.date, send_email=not args.no_email)
    print(f"[完成] 日报生成成功!")


if __name__ == "__main__":
    sys.exit(main())
