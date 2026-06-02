"""
各平台标题 + 话题标签生成器

基于文案内容自动生成适配各平台的标题和话题标签。
遵循平台规则和爆款文案标准。
"""

import re
from platform import PLATFORMS


# ── 标题模板库 ──
# 占位符说明:
#   {n}       = 小数字(1-10), 默认3, 用于"个要点/个步骤/件事"
#   {price}   = 文案中的价格数字
#   {product} = 产品名（床垫/手机/...）
#   {who}     = 人群词
#   {brand1} {brand2} = 品牌名
#   {action}  = 动作词

TITLE_TEMPLATES = {
    "家居": {
        "抖音": [
            "{price}元和{price2}元的{product}，到底差在哪",
            "买{product}千万别买{type}，除非你钱多",
            "行内人告诉你，{product}选错=白花钱",
            "{product}的{n}个真相，第{n2}个没人敢说",
            "后悔才知道，{product}应该这样选",
            "{product}水太深？{n}招教你避坑",
        ],
        "小红书": [
            "{product}怎么选？{n}年经验全分享",
            "{who}必看！{product}选购避坑指南",
            "花冤枉钱买来的教训：{product}千万别将就",
            "{product}选购攻略｜全价位推荐不踩雷",
            "抄作业！{product}这样买不交智商税",
        ],
        "B站": [
            "{product}选购终极指南｜从入门到高端的{n}个真相",
            "为什么{product}行业水这么深？{n}分钟说清楚",
            "{product}深度评测：多少钱才算合理？",
            "从业内到消费者：{product}选购的{n}个认知误区",
        ],
        "视频号": [
            "{product}千万别瞎买！这{n}点最重要",
            "后悔才知道的{product}真相，越贵不等于越好",
            "买{product}记住这{n}句，谁也坑不了你",
        ],
        "快手": [
            "{product}水太深！老铁们记住这{n}点",
            "{product}到底多少钱才合适？行内人说实话",
            "别再被忽悠了！{product}真的不需要买太贵",
        ],
        "YouTube": [
            "{product} | {n} Things You Must Know",
            "Don't Buy {product} Until You Watch This",
            "{product} Review: Is Expensive Really Better?",
        ],
    },
    "数码": {
        "抖音": [
            "华为手机这个功能，90%的人不知道",
            "还在花钱做{action}？{product}一句话就搞定",
            "鸿蒙{n}的{n2}个宝藏功能，用了回不去",
            "你以为{product}只能{action}？它还能...",
            "{who}福音！{product}这个功能真能替你打工",
        ],
        "小红书": [
            "{product}隐藏功能｜第{n}个太香了",
            "{who}进来抄作业！{product}这样设置好用{n}倍",
            "{product}技巧合集｜{n}个提高效率的神操作",
            "后悔没早知道的{product}功能，真的绝了",
        ],
        "B站": [
            "{product}深度体验：{n}个功能实测，有惊喜也有槽点",
            "从{product}看行业趋势：{n}个变化你必须知道",
            "{brand1} vs {brand2}，谁更强？对比评测",
        ],
        "视频号": [
            "{product}这个功能太实用了，很多人都不知道",
            "{product}用户注意！这{n}个设置一定要关",
            "别花冤枉钱！{product}这些功能免费又好用",
        ],
        "快手": [
            "{product}实用技巧！第{n}个真能帮大忙",
            "老铁们，{product}这些功能不用真浪费了",
        ],
        "YouTube": [
            "{product} Tips & Tricks You Need to Know",
            "{brand1} vs {brand2}: Which One Should You Buy?",
        ],
    },
}


# ── 话题标签模板 ──

TAG_TEMPLATES = {
    "家居": {
        "core": ["#家居好物", "#家居", "#装修"],
        "products": {
            "床垫": ["#床垫", "#床垫怎么选", "#床垫推荐", "#床垫测评"],
            "沙发": ["#沙发", "#沙发推荐", "#客厅装修"],
            "灯": ["#灯具", "#灯光设计", "#氛围灯"],
            "窗帘": ["#窗帘", "#窗帘搭配", "#软装"],
            "家具": ["#家具", "#家具推荐", "#家具选购"],
            "空气净化器": ["#空气净化器", "#空气质量", "#家电"],
        },
        "extra": ["#居家好物", "#生活好物", "#避坑指南", "#租房好物", "#干货分享", "#性价比", "#智商税"],
    },
    "数码": {
        "core": ["#数码", "#数码好物"],
        "products": {
            "手机": ["#手机", "#手机推荐", "#手机技巧"],
            "华为": ["#华为", "#华为手机", "#鸿蒙", "#HarmonyOS"],
            "iPhone": ["#iPhone", "#iOS", "#苹果"],
            "耳机": ["#耳机", "#蓝牙耳机", "#降噪耳机"],
            "电脑": ["#电脑", "#笔记本", "#电脑技巧"],
            "平板": ["#平板", "#平板电脑"],
        },
        "extra": ["#科技", "#涨知识", "#干货", "#效率工具", "#数码控", "#隐藏功能"],
    },
}


def extract_keywords(text):
    """从文案中提取关键信息用于模板填充"""
    info = {
        "product": None,
        "type": None,
        "who": None,
        "action": None,
        "brand1": None,
        "brand2": None,
        "n": "3",        # 小数字，用于"几点/几个"
        "n2": "5",
        "price": None,   # 价格数字
        "price2": None,
    }

    # 提取产品词
    product_kw = ["床垫", "手机", "耳机", "沙发", "窗帘", "灯", "电脑", "平板", "家具", "空气净化器"]
    for kw in product_kw:
        if kw in text:
            info["product"] = kw
            break

    # 提取品牌
    brands = ["华为", "苹果", "三星", "小米", "金可儿", "舒达", "丝涟", "席梦思", "喜临门", "雅兰", "梦百合"]
    found_brands = [b for b in brands if b in text]
    if len(found_brands) >= 1:
        info["brand1"] = found_brands[0]
    if len(found_brands) >= 2:
        info["brand2"] = found_brands[1]

    # 提取数字 - 区分价格数字和小数字
    nums = re.findall(r"\d+", text)
    # 过滤掉年份（20xx, 202x, 26xxxx 这类日期数字）
    filtered = [n for n in nums if not (len(n) == 4 and n.startswith("20")) and not (len(n) == 6 and n.startswith("26"))]

    # 价格数字：三位数以上，以1-3开头
    price_nums = [n for n in filtered if len(n) >= 3 and n[0] in "123"]
    # 小数字：个位数
    small_nums = [n for n in filtered if len(n) == 1 and n in "123456789"]
    # 中数字：两位数
    mid_nums = [n for n in filtered if len(n) == 2]

    if price_nums:
        info["price"] = price_nums[0]
        if len(price_nums) > 1:
            info["price2"] = price_nums[1]

    if small_nums:
        info["n"] = small_nums[0]
    if len(small_nums) > 1:
        info["n2"] = small_nums[1]
    elif mid_nums:
        # 没有个位数时，用两位数
        info["n"] = mid_nums[0]

    # 提取动作词
    action_map = {"花钱": "花钱", "设置": "设置", "买": "买", "选": "选", "操作": "操作", "打开": "打开", "关掉": "关掉"}
    for k, v in action_map.items():
        if k in text:
            info["action"] = v
            break

    # 提取人群词
    who_kw = ["打工人", "上班族", "学生党", "租房党", "宝妈", "白领", "老人", "年轻人"]
    for kw in who_kw:
        if kw in text:
            info["who"] = kw
            break

    return info


def generate_title(platform, category, keywords, article_text):
    """
    为指定平台生成标题
    """
    pf_config = PLATFORMS.get(platform)
    if not pf_config:
        return article_text[:20], ""

    max_len = pf_config["title_recommended"]
    templates = TITLE_TEMPLATES.get(category, {}).get(platform, [])

    if not templates:
        return _rule_based_title(pf_config, article_text, keywords), ""

    # 填充模板
    filler = {
        "n": keywords.get("n", "3"),
        "n2": keywords.get("n2", "5"),
        "price": keywords.get("price") or keywords.get("n", "1000"),
        "price2": keywords.get("price2") or keywords.get("n2", "5000"),
        "product": keywords.get("product") or "这个",
        "type": keywords.get("type") or "xx",
        "who": keywords.get("who") or "很多人",
        "action": keywords.get("action") or "做",
        "brand1": keywords.get("brand1") or "A牌",
        "brand2": keywords.get("brand2") or "B牌",
    }

    candidates = []
    for tpl in templates:
        try:
            title = tpl
            for k, v in filler.items():
                placeholder = "{" + k + "}"
                if placeholder in title:
                    title = title.replace(placeholder, str(v))
            # 清理剩余占位符
            title = re.sub(r"\{[^}]+\}", "", title)
            title = re.sub(r"\s+", " ", title)
            title = title.strip().rstrip(",").rstrip("，")

            if title and len(title) <= max_len:
                candidates.append(title)
        except Exception:
            continue

    if candidates:
        chosen = candidates[0]
    else:
        chosen = _rule_based_title(pf_config, article_text, keywords)

    suggestions = pf_config.get("title_rules", [])
    tips = "；".join(suggestions) if suggestions else ""
    return chosen, tips


def _rule_based_title(pf_config, article_text, keywords):
    """基于规则的标题生成（无模板时的后备方案）"""
    max_len = pf_config["title_recommended"]
    product = keywords.get("product") or "这个"

    # 从文案首行提取
    first_line = article_text.strip().split("\n")[0][:max_len]
    if first_line and len(first_line) <= max_len:
        return first_line

    # 组合
    pattern = f"{product}选购的几点真相"
    return pattern[:max_len]


def generate_tags(platform, category, keywords, article_text):
    """
    为指定平台生成话题标签
    """
    pf_config = PLATFORMS.get(platform)
    min_tags, max_tags = pf_config["tag_count"]

    tag_data = TAG_TEMPLATES.get(category, {})
    if not tag_data:
        tag_data = {"core": ["#" + category], "products": {}, "extra": ["#干货", "#推荐"]}

    core = list(tag_data.get("core", []))
    products = tag_data.get("products", {})
    extra = list(tag_data.get("extra", []))

    selected = []

    # 1. 核心标签
    selected.extend(core)

    # 2. 产品标签
    product = keywords.get("product")
    if product and product in products:
        selected.extend(products[product])

    # 3. 品牌标签
    brand = keywords.get("brand1")
    if brand:
        selected.append(f"#{brand}")

    # 4. 补充到上限
    for tag in extra:
        if tag not in selected and len(selected) < max_tags:
            selected.append(tag)

    # 5. 还不够？从文案提取关键词
    if len(selected) < min_tags:
        for kw in _extract_hashtag_keywords(article_text):
            tag = f"#{kw}"
            if tag not in selected and len(selected) < max_tags:
                selected.append(tag)

    return selected[:max_tags]


def _extract_hashtag_keywords(text):
    """从文案中提取适合做话题标签的关键词"""
    important = [
        "干货", "避坑", "测评", "推荐", "选购", "攻略",
        "智商税", "平替", "省钱", "教程", "技巧", "隐藏功能",
        "性价比", "深度体验", "开箱", "使用感受",
        "对比", "评测", "必看", "真相",
    ]
    return [kw for kw in important if kw in text][:5]


def full_generation(article_info, platforms=None):
    """
    为指定/所有平台生成标题和话题标签

    返回:
        [{platform, title, tags, suggestions}, ...]
    """
    if platforms is None:
        platforms = list(PLATFORMS.keys())

    text = article_info["content"]
    category = article_info["category"]
    keywords = extract_keywords(text)

    results = []
    for pname in platforms:
        if pname not in PLATFORMS:
            continue
        title, tips = generate_title(pname, category, keywords, text)
        tags = generate_tags(pname, category, keywords, text)
        results.append({
            "platform": pname,
            "title": title,
            "tags": tags,
            "suggestions": tips,
        })

    return results
