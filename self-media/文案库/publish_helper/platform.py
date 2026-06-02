"""
各平台发布规则配置
- 标题长度限制（字符数）
- 话题标签规则
- 封面图尺寸（宽×高，像素，含多种宽高比）
- 内容风格特点

数据来源：各平台官方/创作者文档，2026年
"""

PLATFORMS = {
    "抖音": {
        "name": "抖音",
        "name_en": "douyin",
        "title_max": 55,          # 官方限制 55字
        "title_recommended": 25,  # 推荐 ≤25（feed只显示约24字）
        "tag_count": (3, 5),      # 可加10个，建议3-5
        "video_ratio": "9:16",
        "cover_sizes": [          # 列表，主尺寸在前
            {"size": (1080, 1920), "ratio": "9:16", "note": "竖屏全屏"},
            {"size": (1080, 1440), "ratio": "3:4", "note": "feed封面"},
        ],
        "style": "快节奏/强钩子/前3秒定生死/口语化",
        "title_rules": [
            "必须包含数字或具体数据",
            "前3秒要有悬念/痛点/反常识",
            "禁用'家人们'等过度营销话术",
        ],
        "tag_rules": [
            "包含领域话题 + 具体产品话题",
            "2-3个精准标签 + 1个个人品牌标签",
        ],
    },
    "小红书": {
        "name": "小红书",
        "name_en": "xiaohongshu",
        "title_max": 24,          # 2行×12字上限
        "title_recommended": 18,
        "tag_count": (8, 15),     # 最多20个，建议10-15
        "video_ratio": "3:4 / 9:16",
        "cover_sizes": [
            {"size": (1080, 1440), "ratio": "3:4", "note": "feed封面（最常用）"},
            {"size": (1080, 1920), "ratio": "9:16", "note": "竖屏视频"},
            {"size": (1080, 1080), "ratio": "1:1", "note": "正方形"},
        ],
        "style": "干货感/可收藏/信息密度高/痛点共鸣",
        "title_rules": [
            "公式：人群+痛点+解决方案/数字",
            "15-25字，要有数字冲击或悬念词",
            "禁用标题党（被举报会限流）",
        ],
        "tag_rules": [
            "数量要足，8-15个精准关键词",
            "包含品类词+场景词+人群词",
            "前3个标签最重要，放最精准的",
        ],
    },
    "B站": {
        "name": "B站",
        "name_en": "bilibili",
        "title_max": 30,          # 约30汉字
        "title_recommended": 25,
        "tag_count": (3, 5),      # 最多10个，建议3-5
        "video_ratio": "16:9",
        "cover_sizes": [
            {"size": (1920, 1080), "ratio": "16:9", "note": "横屏标准"},
            {"size": (1440, 1080), "ratio": "4:3", "note": "备用"},
        ],
        "style": "深度内容/干货/有观点/年轻人语感",
        "title_rules": [
            "可以稍长，但要信息完整",
            "适合用'为什么''怎么''测评'类句式",
            "可以有副标题/冒号分隔",
        ],
        "tag_rules": [
            "3-5个精准标签",
            "第一个标签最重要",
        ],
    },
    "视频号": {
        "name": "视频号",
        "name_en": "shipinhao",
        "title_max": 24,          # 约24字（2行）
        "title_recommended": 18,
        "tag_count": (3, 8),      # 最多15个，建议3-8
        "video_ratio": "9:16",
        "cover_sizes": [
            {"size": (1080, 1920), "ratio": "9:16", "note": "竖屏视频"},
            {"size": (1080, 1260), "ratio": "6:7", "note": "feed封面"},
        ],
        "style": "微信生态/社交传播/信任感/接地气",
        "title_rules": [
            "短小精悍，≤20字",
            "微信生态，标题要让人有点开的欲望",
            "适合用'千万别''后悔才知道'类句式",
        ],
        "tag_rules": [
            "3-8个标签",
            "精准不贪多，前3个最重要",
        ],
    },
    "快手": {
        "name": "快手",
        "name_en": "kuaishou",
        "title_max": 40,
        "title_recommended": 25,
        "tag_count": (3, 5),      # 最多10个，建议3-5
        "video_ratio": "9:16",
        "cover_sizes": [
            {"size": (1080, 1920), "ratio": "9:16", "note": "竖屏"},
        ],
        "style": "接地气/真实感/贴近生活/老铁文化",
        "title_rules": [
            "实在、直接、不装",
            "可以用'老铁''兄弟们'等亲切称呼",
            "数字和实践经验更受欢迎",
        ],
        "tag_rules": [
            "3-5个相关话题标签",
            "蹭热点话题效果好",
        ],
    },
    "YouTube": {
        "name": "YouTube",
        "name_en": "youtube",
        "title_max": 100,
        "title_recommended": 60,
        "tag_count": (3, 5),      # 标签在描述中
        "video_ratio": "16:9",
        "cover_sizes": [
            {"size": (1280, 720), "ratio": "16:9", "note": "缩略图标准尺寸"},
        ],
        "style": "SEO驱动/长尾关键词/缩略图至关重要",
        "title_rules": [
            "SEO关键词前置",
            "可以包含数字、括号、竖线等符号",
            "100字符以内，但推荐50-60字符",
        ],
        "tag_rules": [
            "标签在描述中，按重要程度排序",
            "包含主关键词+长尾词",
        ],
    },
}


def get_platform(name):
    """根据中文名获取平台配置"""
    return PLATFORMS.get(name)


def list_platforms():
    """列出所有平台及其规则"""
    print(f"  {'平台':6s}  |  {'视频比例':>8s}  |  {'封面尺寸选项':>20s}  |  {'标题上限':>8s}  |  标签数量")
    print("  " + "-" * 85)
    for name, cfg in PLATFORMS.items():
        sizes = ", ".join(f"{s['size'][0]}×{s['size'][1]}({s['ratio']})" for s in cfg["cover_sizes"])
        print(f"  {name:6s}  |  {cfg['video_ratio']:>8s}  |  {sizes:>36s}  |  ≤{cfg['title_max']:>2d}字  |  {cfg['tag_count'][0]}-{cfg['tag_count'][1]}个")
