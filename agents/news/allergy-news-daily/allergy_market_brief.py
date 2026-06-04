#!/usr/bin/env python3
"""
US Allergy Clinics Market Brief - 美国过敏诊所市场简报
功能：通过Google News RSS搜索近7天美国过敏诊所市场新闻，
      DeepSeek AI分析后输出Top 10，每条的3维度分析，
      生成.md和HTML报告，发到163邮箱。
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta

try:
    import requests
    import feedparser
except ImportError:
    print("Error: Please install requests and feedparser")
    sys.exit(1)

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = "sk-5b6edf2647fd43898aafeefe4c7763d8"

# 搜索关键词（覆盖面更广，确保返回足够结果）
SEARCH_KEYWORDS = [
    "allergy clinic United States",
    "allergy immunotherapy market business",
    "food allergy treatment FDA approval",
    "allergy testing diagnostic market",
    "allergy practice private equity acquisition",
    "allergy clinic merger partnership",
    "allergy healthcare investment funding",
    "allergy biologics treatment market",
    "allergy physician specialist United States",
    "allergy telemedicine digital health clinic",
    "asthma allergy clinic expansion",
    "allergy drug development clinical trial",
]

# 来源可信度
SOURCE_CREDIBILITY = {
    "AAAAI": 100, "ACAAI": 100, "Allergy & Asthma Network": 100,
    "American College of Allergy, Asthma & Immunology": 100,
    "American Academy of Allergy, Asthma & Immunology": 100,
    "Fierce Healthcare": 80, "Fierce Pharma": 80, "Fierce Biotech": 80,
    "Fierce MedTech": 80, "Endpoints News": 80,
    "Modern Healthcare": 75, "Beckers Hospital Review": 70,
    "Reuters": 70, "STAT News": 70,
    "Medscape": 90, "PitchBook": 60, "Crunchbase": 60,
    "MedTech Dive": 65, "Business Wire": 60, "PR Newswire": 50,
    "Yahoo Finance": 45, "Seeking Alpha": 45,
    "Forbes": 55, "Bloomberg": 60, "Wall Street Journal": 65,
    "New York Times": 55, "Google News": 50,
}


def _clean_html(text):
    """清理HTML标签和实体"""
    if not text:
        return ""
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    text = " ".join(text.split())
    return text.strip()


def _extract_source(url):
    """从URL提取来源名称用于可信度评估"""
    domain_map = {
        "aaaai.org": "AAAAI",
        "acaai.org": "ACAAI",
        "allergyasthmanetwork.org": "Allergy & Asthma Network",
        "fiercehealthcare.com": "Fierce Healthcare",
        "fiercepharma.com": "Fierce Pharma",
        "fiercebiotech.com": "Fierce Biotech",
        "fiercemedtech.com": "Fierce MedTech",
        "endpts.com": "Endpoints News",
        "modernhealthcare.com": "Modern Healthcare",
        "beckershospitalreview.com": "Beckers Hospital Review",
        "reuters.com": "Reuters",
        "statnews.com": "STAT News",
        "medscape.com": "Medscape",
        "pitchbook.com": "PitchBook",
        "crunchbase.com": "Crunchbase",
        "medtechdive.com": "MedTech Dive",
        "businesswire.com": "Business Wire",
        "prnewswire.com": "PR Newswire",
        "finance.yahoo.com": "Yahoo Finance",
        "seekingalpha.com": "Seeking Alpha",
        "forbes.com": "Forbes",
        "bloomberg.com": "Bloomberg",
        "wsj.com": "Wall Street Journal",
        "nytimes.com": "New York Times",
    }
    if not url:
        return "Google News"
    for domain, name in domain_map.items():
        if domain in url:
            return name
    return "Google News"


def search_us_market_news(days_back=7):
    """通过Google News RSS搜索美国过敏诊所市场新闻，返回最多50条"""
    all_items = []
    seen_titles = set()
    cutoff = datetime.now() - timedelta(days=days_back)

    for keyword in SEARCH_KEYWORDS:
        encoded = keyword.replace(" ", "+")
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = requests.get(
                rss_url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code != 200:
                print(f"  [RSS] Failed: {keyword[:40]}... (HTTP {resp.status_code})")
                continue

            feed = feedparser.parse(resp.text)
            count = 0
            for entry in feed.entries:
                title = _clean_html(entry.get("title", ""))
                if not title or title in seen_titles:
                    continue

                # 时间过滤
                published = entry.get("published", "") or entry.get("updated", "")
                if published:
                    try:
                        from email.utils import parsedate_to_datetime
                        pub_date = parsedate_to_datetime(published)
                        if pub_date.replace(tzinfo=None) < cutoff:
                            continue
                    except Exception:
                        pass  # 无法解析日期则保留

                seen_titles.add(title)
                link = entry.get("link", "")
                snippet = _clean_html(
                    entry.get("summary", "")
                    or entry.get("description", "")
                    or ""
                )[:500]
                source = _extract_source(link)

                all_items.append(
                    {
                        "title": title,
                        "url": link,
                        "snippet": snippet,
                        "source": source,
                        "published": published,
                        "search_keyword": keyword,
                    }
                )
                count += 1
            print(f"  [RSS] {keyword[:40]}... → {count} items")
        except Exception as e:
            print(f"  [RSS] Error for '{keyword[:40]}...': {str(e)[:60]}")

    # 去重后按发表时间排序，取前50
    all_items.sort(
        key=lambda x: x.get("published", ""),
        reverse=True,
    )
    result = all_items[:50]
    print(f"  [Search] Total unique: {len(result)} items")
    return result


def analyze_with_deepseek(item):
    """调用DeepSeek API分析单条新闻，返回结构化分析文本"""
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    source = item.get("source", "")

    prompt = f"""你是一位专注于美国过敏诊所市场的医疗器械行业分析师。请分析以下新闻，用中文输出。

新闻标题：{title}
内容摘要：{snippet}
来源：{source}

请按以下格式输出（严格遵守格式）：

【重要性评分】X/10
【事件概述】用2-3句话概括这条新闻发生了什么
【为什么重要】分析为什么这条新闻对美国过敏诊所市场重要（1-2句话）
【器械耗材关联】分析这条新闻与美国过敏诊所使用的医疗器械、耗材、设备之间有什么关联，以及可能的商业机会（1-2句话）"""

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专注于美国过敏诊所市场的医疗器械行业分析师。请严格按照要求的格式输出分析结果。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 500,
        }

        response = requests.post(
            DEEPSEEK_API_URL, headers=headers, json=data, timeout=45
        )
        if response.status_code == 200:
            result = response.json()
            content = (
                result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if content:
                print(f"  [DeepSeek] Analysis OK for: {title[:50]}...")
                return content
        elif response.status_code == 402:
            print(f"  [DeepSeek] API balance insufficient (402)")
        else:
            print(f"  [DeepSeek] API error {response.status_code}")
    except Exception as e:
        print(f"  [DeepSeek] Request failed: {str(e)[:50]}")

    # 降级：规则提取
    return _fallback_analysis(item)


def _fallback_analysis(item):
    """DeepSeek不可用时的降级分析"""
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    score = 5  # 默认中等评分

    # 简单启发式评分
    text = (title + " " + snippet).lower()
    if any(k in text for k in ["acquisition", "merger", "acquire", "merge", "收购", "并购"]):
        score = 8
    elif any(k in text for k in ["funding", "investment", "series ", "ipo", "融资", "上市"]):
        score = 7
    elif any(k in text for k in ["expansion", "growth", "expand", "扩张", "增长"]):
        score = 7
    elif any(k in text for k in ["partnership", "collaboration", "合作"]):
        score = 6
    elif any(k in text for k in ["telemedicine", "telehealth", "telehealthcare", "远程"]):
        score = 6
    elif any(k in text for k in ["product launch", "fda", "approval", "获批"]):
        score = 7

    return f"""【重要性评分】{score}/10
【事件概述】{title}。{snippet[:200]}
【为什么重要】此新闻涉及美国过敏诊所市场的重要动态。
【器械耗材关联】该事件可能影响美国过敏诊所的器械和耗材需求。"""


def parse_analysis(raw):
    """正则解析DeepSeek返回的4个字段"""
    result = {
        "importance_score": 5,
        "event_summary": "分析暂时不可用",
        "why_important": "分析暂时不可用",
        "device_relevance": "分析暂时不可用",
    }

    if not raw:
        return result

    patterns = {
        "importance_score": r"【重要性评分】\s*(\d+)\s*/?\s*10",
        "event_summary": r"【事件概述】\s*(.+?)(?=\n【|$)",
        "why_important": r"【为什么重要】\s*(.+?)(?=\n【|$)",
        "device_relevance": r"【器械耗材关联】\s*(.+?)(?=\n【|$)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            value = match.group(1).strip()
            if field == "importance_score":
                try:
                    result[field] = min(10, max(1, int(value)))
                except ValueError:
                    pass
            else:
                result[field] = value if value else result[field]

    return result


def sort_by_importance(news):
    """综合评分排序：DeepSeek评分(40%) + 来源可信度(30%) + 时效性(30%)"""
    scored = []
    for item in news:
        ds_score = item.get("importance_score", 5)
        src_name = item.get("source", "")
        credibility = SOURCE_CREDIBILITY.get(src_name, 50)

        # 时效性
        recency = 50
        published = item.get("published", "")
        if published:
            try:
                from email.utils import parsedate_to_datetime
                pub_date = parsedate_to_datetime(published)
                hours_old = (datetime.now() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
                if hours_old < 6:
                    recency = 100
                elif hours_old < 24:
                    recency = 90
                elif hours_old < 48:
                    recency = 70
                elif hours_old < 72:
                    recency = 50
                else:
                    recency = 30
            except Exception:
                pass

        composite = (ds_score * 10 * 0.4) + (credibility * 0.3) + (recency * 0.3)
        item["composite_score"] = round(composite, 1)
        scored.append(item)

    scored.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    return scored[:10]


def _format_time_ago(published):
    """格式化时间显示"""
    if not published:
        return ""
    try:
        from email.utils import parsedate_to_datetime
        pub_date = parsedate_to_datetime(published)
        hours_old = (datetime.now() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
        if hours_old < 1:
            return "刚刚"
        elif hours_old < 24:
            return f"{int(hours_old)}小时前"
        elif hours_old < 48:
            return "昨天"
        else:
            return f"{int(hours_old // 24)}天前"
    except Exception:
        return ""


def generate_markdown(news, date_str):
    """生成结构化.md报告"""
    today_formatted = datetime.now().strftime("%Y年%m月%d日")
    stars = lambda s: "★" * min(5, max(1, s // 2))

    lines = [
        f"# 美国过敏诊所市场简报",
        f"",
        f"**日期**: {date_str} ({today_formatted})",
        f"**数据来源**: Google News RSS (美国市场)",
        f"**分析工具**: DeepSeek AI",
        f"",
        f"---",
        f"",
        f"## Top 10 市场要闻",
        f"",
    ]

    for i, item in enumerate(news, 1):
        score = item.get("importance_score", 5)
        composite = item.get("composite_score", 0)
        lines.append(f"### {i}. {item['title']}")
        lines.append(f"")
        lines.append(f"- **综合评分**: {composite} | **重要性**: {stars(score)} ({score}/10)")
        lines.append(f"- **来源**: {item.get('source', 'Unknown')}")
        lines.append(f"- **时间**: {_format_time_ago(item.get('published', ''))}")
        lines.append(f"- **原文**: {item.get('url', '#')}")
        lines.append(f"")
        lines.append(f"**事件概述**: {item.get('event_summary', '')}")
        lines.append(f"")
        lines.append(f"**为什么重要**: {item.get('why_important', '')}")
        lines.append(f"")
        lines.append(f"**器械耗材关联**: {item.get('device_relevance', '')}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

    lines.append(f"")
    lines.append(f"*本简报由 Allergy Market Brief 自动生成 · {date_str}*")

    return "\n".join(lines)


def fetch_and_analyze(date_str=None):
    """主流程编排：搜索 → 分析 → 排序 → 生成报告"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"[Market Brief] 开始生成 {date_str} 美国过敏诊所市场简报...")

    # Step 1: 搜索
    print("\n[Step 1] 搜索美国过敏诊所市场新闻...")
    raw_news = search_us_market_news(days_back=7)

    if not raw_news:
        print("[Market Brief] 未搜索到任何新闻，终止。")
        return {"error": "no_news", "count": 0}

    # Step 2: DeepSeek分析
    print(f"\n[Step 2] DeepSeek分析 ({len(raw_news)} 条)...")
    analyzed = []
    for i, item in enumerate(raw_news, 1):
        print(f"  [{i}/{len(raw_news)}] Analyzing: {item['title'][:60]}...")
        raw_analysis = analyze_with_deepseek(item)
        parsed = parse_analysis(raw_analysis)
        item.update(parsed)
        analyzed.append(item)

    # Step 3: 排序
    print(f"\n[Step 3] 综合评分排序...")
    top10 = sort_by_importance(analyzed)

    # Step 4: 生成报告
    print(f"\n[Step 4] 生成报告...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "output", date_str)
    os.makedirs(output_dir, exist_ok=True)

    # Markdown
    md_content = generate_markdown(top10, date_str)
    md_path = os.path.join(output_dir, "allergy_market_brief.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"  [Saved] {md_path}")

    # JSON
    json_path = os.path.join(output_dir, "allergy_market_brief.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": date_str,
                "count": len(top10),
                "total_searched": len(raw_news),
                "news": top10,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"  [Saved] {json_path}")

    return {
        "date": date_str,
        "count": len(top10),
        "total_searched": len(raw_news),
        "news": top10,
        "markdown_path": md_path,
        "json_path": json_path,
        "output_dir": output_dir,
    }


if __name__ == "__main__":
    result = fetch_and_analyze()
    if "error" in result:
        print(f"\n[Market Brief] Failed: {result['error']}")
        sys.exit(1)
    print(f"\n[Market Brief] Done! {result['count']} items saved.")
