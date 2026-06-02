#!/usr/bin/env python3
"""
Allergy News Sources - 过敏专业新闻源采集器
整合EAACI, AAAAI, ACAAI, ASCIA, Medscape等12个专业过敏/免疫学新闻源
"""

import json
import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup


# 过敏专业新闻源配置
ALLERGY_SOURCES = [
    # 欧洲
    {
        "name": "EAACI",
        "source_name": "European Academy of Allergy and Clinical Immunology",
        "region": "Europe",
        "url": "https://www.eaaci.org/news",
        "type": "professional_org",
        "parser": "html"
    },
    {
        "name": "BSACI",
        "source_name": "British Society for Allergy & Clinical Immunology",
        "region": "Europe",
        "url": "https://bsaci.org/news/",
        "type": "professional_org",
        "parser": "html"
    },
    {
        "name": "DGAKI",
        "source_name": "German Society for Allergology and Clinical Immunology",
        "region": "Europe",
        "url": "https://www.dgaki.de/en/",
        "type": "professional_org",
        "parser": "html"
    },

    # 美国
    {
        "name": "AAAAI",
        "source_name": "American Academy of Allergy, Asthma & Immunology",
        "region": "USA",
        "url": "https://www.aaaai.org/news-media",
        "type": "professional_org",
        "parser": "html"
    },
    {
        "name": "ACAAI",
        "source_name": "American College of Allergy, Asthma & Immunology",
        "region": "USA",
        "url": "https://acaai.org/news/",
        "type": "professional_org",
        "parser": "html"
    },
    {
        "name": "Allergy & Asthma Network",
        "source_name": "Allergy & Asthma Network",
        "region": "USA",
        "url": "https://allergyasthmanetwork.org/",
        "type": "patient_advocacy",
        "parser": "html"
    },
    {
        "name": "Becker's Hospital Review - Allergy",
        "source_name": "Becker's Hospital Review Allergy & Pulmonology",
        "region": "USA",
        "url": "https://www.beckershospitalreview.com/allergy-pulmonology.html",
        "type": "medical_news",
        "parser": "html"
    },

    # 澳洲
    {
        "name": "ASCIA",
        "source_name": "Australasian Society of Clinical Immunology and Allergy",
        "region": "Australia",
        "url": "https://www.allergy.org.au/",
        "type": "professional_org",
        "parser": "html"
    },
    {
        "name": "AusDoc",
        "source_name": "AusDoc - Australian Doctor",
        "region": "Australia",
        "url": "https://www.ausdoc.com.au/",
        "type": "medical_news",
        "parser": "html"
    },
    {
        "name": "Medical Republic",
        "source_name": "Medical Republic Australia",
        "region": "Australia",
        "url": "https://www.medicalrepublic.com.au/",
        "type": "medical_news",
        "parser": "html"
    },
    {
        "name": "NewsGP",
        "source_name": "NewsGP - RACGP",
        "region": "Australia",
        "url": "https://www.newsgp.com.au/",
        "type": "medical_news",
        "parser": "html"
    },
    {
        "name": "RACGP",
        "source_name": "Royal Australian College of General Practitioners",
        "region": "Australia",
        "url": "https://www.racgp.org.au/",
        "type": "professional_org",
        "parser": "html"
    },
    {
        "name": "National Allergy Council",
        "source_name": "National Allergy Council Australia",
        "region": "Australia",
        "url": "https://www.nationalallergycouncil.org.au/",
        "type": "professional_org",
        "parser": "html"
    },

    # 国际
    {
        "name": "Medscape Allergy",
        "source_name": "Medscape Allergy & Immunology",
        "region": "International",
        "url": "https://www.medscape.com/",
        "type": "medical_news",
        "parser": "html"
    },
    {
        "name": "Fierce Healthcare",
        "source_name": "Fierce Healthcare",
        "region": "International",
        "url": "https://www.fiercehealthcare.com/",
        "type": "medical_news",
        "parser": "html"
    },

    # =========================================================================
    # 通用医疗行业新闻源 (可能涉及所有三类企业，需Agent内部关键词筛选)
    # =========================================================================
    {
        "name": "Modern Healthcare",
        "source_name": "Modern Healthcare",
        "region": "USA",
        "url": "https://www.modernhealthcare.com/",
        "type": "medical_news",
        "parser": "html"
    },
    {
        "name": "Reuters Health",
        "source_name": "Reuters Health",
        "region": "International",
        "url": "https://www.reuters.com/business/healthcare-pharmaceuticals/",
        "type": "medical_news",
        "parser": "html"
    },

    # =========================================================================
    # 连锁过敏诊所集团
    # =========================================================================
    {
        "name": "PitchBook",
        "source_name": "PitchBook - VC/PE Database",
        "region": "International",
        "url": "https://pitchbook.com/news/articles",
        "type": "investment",
        "parser": "html"
    },
    {
        "name": "Crunchbase",
        "source_name": "Crunchbase - Startup Database",
        "region": "International",
        "url": "https://news.crunchbase.com/",
        "type": "investment",
        "parser": "html"
    },

    # =========================================================================
    # 过敏诊断设备制造商
    # =========================================================================
    {
        "name": "MedTech Dive",
        "source_name": "MedTech Dive",
        "region": "International",
        "url": "https://www.medtechdive.com/news/",
        "type": "medtech",
        "parser": "html"
    },
    {
        "name": "Fierce MedTech",
        "source_name": "Fierce MedTech",
        "region": "International",
        "url": "https://www.fiercemedtech.com/latest-news",
        "type": "medtech",
        "parser": "html"
    },
    {
        "name": "AACC Clinical Lab News",
        "source_name": "AACC Clinical Laboratory News",
        "region": "International",
        "url": "https://www.aacc.org/news-and-pubs/clinical-laboratory-news",
        "type": "medtech",
        "parser": "html"
    },

    # =========================================================================
    # 过敏药物研发公司
    # =========================================================================
    {
        "name": "Fierce Pharma",
        "source_name": "Fierce Pharma",
        "region": "International",
        "url": "https://www.fiercepharma.com/latest-news",
        "type": "pharma",
        "parser": "html"
    },
    {
        "name": "Fierce Biotech",
        "source_name": "Fierce Biotech",
        "region": "International",
        "url": "https://www.fiercebiotech.com/latest-news",
        "type": "biotech",
        "parser": "html"
    },
    {
        "name": "Endpoints News",
        "source_name": "Endpoints News",
        "region": "International",
        "url": "https://endpts.com/latest-news/",
        "type": "biotech",
        "parser": "html"
    },
    {
        "name": "STAT News",
        "source_name": "STAT News - Biopharma",
        "region": "USA",
        "url": "https://www.statnews.com/tag/biopharma/",
        "type": "biotech",
        "parser": "html"
    },
    {
        "name": "ClinicalTrials.gov",
        "source_name": "ClinicalTrials.gov - Allergy Trials",
        "region": "International",
        "url": "https://clinicaltrials.gov/search?term=allergy&aggFilters=status:rec,not_rec",
        "type": "clinical_trials",
        "parser": "html"
    }
]


def clean_html_text(text):
    """清理HTML标签"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#39;', "'").replace('&quot;', '"')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_rss_feed(xml_content, source_name, region):
    """解析RSS feed"""
    news_list = []
    soup = BeautifulSoup(xml_content, 'lxml-xml')

    items = soup.find_all('item') or soup.find_all('entry')
    for item in items[:15]:
        title = clean_html_text(item.find('title').get_text() if item.find('title') else "")
        link = item.find('link').get_text() if item.find('link') else ""
        if not link and item.find('link'):
            link = item.find('link').get('href', '')

        description = ""
        desc_tag = item.find('description') or item.find('summary') or item.find('content')
        if desc_tag:
            description = clean_html_text(desc_tag.get_text())

        published = ""
        pub_tag = item.find('pubDate') or item.find('published') or item.find('updated')
        if pub_tag:
            published = pub_tag.get_text()

        if title:
            news_list.append({
                "title": title,
                "url": link,
                "snippet": description[:200] if description else "",
                "keyword": source_name,
                "region": region,
                "published": published,
                "source_type": "rss"
            })

    return news_list


def parse_html_page(html_content, source_name, region):
    """解析HTML页面 - 通用方法"""
    news_list = []
    soup = BeautifulSoup(html_content, 'html.parser')

    # 优先查找文章链接列表模式
    link_patterns = [
        ('a[href*="/news/"]', 'news'),
        ('a[href*="/article"]', 'article'),
        ('a[href*="/blog"]', 'blog'),
        ('.news-item a', 'news-item'),
        ('.article-item a', 'article'),
        ('article a', 'article'),
        ('.post a', 'post'),
        ('.views-row a', 'views'),
        ('h2 a', 'h2'),
        ('h3 a', 'h3'),
        ('h4 a', 'h4'),
    ]

    seen_urls = set()

    for selector, ptype in link_patterns:
        items = soup.select(selector)
        if items:
            for item in items[:20]:
                # 获取标题
                title = clean_html_text(item.get_text())
                href = item.get('href', '')

                # 清理标题 - 移除"Read more"等无意义文字
                title = re.sub(r'^(Read more|Read More|More|Continue reading|Lees meer|Lire la suite|Ver más|mehr|更多)\s*', '', title, flags=re.IGNORECASE)

                if not title or len(title) < 15:
                    continue

                # 跳过分类链接
                skip_words = ['category', 'categories', 'tag', 'tags', 'archive', 'archives', 'announcement', 'latest news', 'older posts', 'older entries']
                if any(sw.lower() in title.lower() for sw in skip_words):
                    continue

                # 处理URL
                if href:
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            # 尝试提取域名
                            base_match = re.search(r'https?://[^/]+', html_content)
                            if base_match:
                                href = base_match.group(0) + href
                        else:
                            href = "https://" + href

                if href and href not in seen_urls:
                    seen_urls.add(href)

                    news_list.append({
                        "title": title,
                        "url": href,
                        "snippet": f"[{ptype}] {source_name} news article",
                        "keyword": source_name,
                        "region": region,
                        "published": "",
                        "source_type": "html"
                    })

    # 如果没有找到，尝试查找RSS或Atom链接
    if not news_list:
        feed_links = soup.select('link[type*="rss"], link[type*="atom"], a[href*="feed"], a[href*="rss"]')
        for link in feed_links[:3]:
            href = link.get('href', '')
            title = link.get('title', 'RSS Feed')
            if href:
                news_list.append({
                    "title": f"RSS Feed: {title}",
                    "url": href,
                    "snippet": "RSS/Atom feed available",
                    "keyword": source_name,
                    "region": region,
                    "published": "",
                    "source_type": "feed"
                })

    return news_list[:15]


def fetch_source(source, timeout=15):
    """抓取单个新闻源"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = requests.get(source['url'], headers=headers, timeout=timeout)
        response.raise_for_status()

        if source['parser'] == 'rss':
            return parse_rss_feed(response.text, source['name'], source['region'])
        else:
            return parse_html_page(response.text, source['name'], source['region'])

    except Exception as e:
        print(f"  [{source['name']}] Error: {str(e)[:50]}")
        return []


def fetch_all_allergy_news():
    """抓取所有过敏新闻源的新闻"""
    all_news = []
    successful = 0

    print("Starting allergy news collection from {} sources...".format(len(ALLERGY_SOURCES)))

    for source in ALLERGY_SOURCES:
        print(f"[Fetching] {source['name']} ({source['region']})...")
        news = fetch_source(source)

        if news:
            all_news.extend(news)
            successful += 1
            print(f"  -> Got {len(news)} articles")
        else:
            print(f"  -> No articles fetched")

    # 去重
    seen = set()
    unique_news = []
    for n in all_news:
        title_key = n.get('title', '')[:80]
        if title_key and title_key not in seen:
            seen.add(title_key)
            unique_news.append(n)

    print(f"\nCollection complete: {len(unique_news)} articles from {successful}/{len(ALLERGY_SOURCES)} sources")

    return unique_news


def save_allergy_news(news_list, output_dir=None, date_str=None):
    """保存过敏新闻到JSON文件"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    if not output_dir:
        output_dir = os.path.join(os.path.dirname(__file__), "output")

    date_dir = os.path.join(output_dir, date_str)
    os.makedirs(date_dir, exist_ok=True)

    output_file = os.path.join(date_dir, "allergy_news.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "date": date_str,
            "count": len(news_list),
            "sources": [s['name'] for s in ALLERGY_SOURCES],
            "news": news_list
        }, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {output_file}")
    return output_file


if __name__ == "__main__":
    news = fetch_all_allergy_news()
    save_allergy_news(news)
