"""
CampusMatch 信息爬取模块

参考日报系统的多源搜索 → 结构化提取 pipeline：
  1. 搜索高校公开的兴趣/活动数据
  2. 提取关键词/标签
  3. 更新 SCHOOL_INTEREST_SEEDS 供新用户冷启动推荐

使用方式：
  - 命令行: python crawler.py --school 澳门大学
  - 作为模块: from crawler import enrich_school_tags

注意：只爬取公开可访问的网页数据，遵守 robots.txt。
"""

import json
import re
import os
from collections import Counter
from datetime import datetime

# 依赖：pip install requests beautifulsoup4
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# 高校公开信息源（不需要登录）
PUBLIC_SOURCES = {
    "澳门大学": {
        "homepage": "https://www.um.edu.mo",
        "student_orgs": "https://sa.um.edu.mo",
        "search_terms": [
            "澳门大学 学生 社团 活动",
            "澳门大学 校园 兴趣 爱 好",
            "UM Macau student life club",
        ],
    },
    "澳门科技大学": {
        "homepage": "https://www.must.edu.mo",
        "search_terms": [
            "澳门科技大学 学生 社团",
            "澳门科技大学 校园 活动",
            "MUST Macau student activities",
        ],
    },
    "澳门理工大学": {
        "homepage": "https://www.mpu.edu.mo",
        "search_terms": [
            "澳门理工大学 学生 社团",
            "MPU Macau campus life",
        ],
    },
    "澳门旅游大学": {
        "homepage": "https://www.iftm.edu.mo",
        "search_terms": [
            "澳门旅游大学 学生 活动",
            "IFTM student activities",
        ],
    },
    "香港大学": {
        "homepage": "https://www.hku.hk",
        "search_terms": [
            "香港大学 学生 社团 兴趣",
            "HKU student societies clubs",
        ],
    },
    "香港中文大学": {
        "homepage": "https://www.cuhk.edu.hk",
        "search_terms": [
            "香港中文大学 学生 活动",
            "CUHK student life activities",
        ],
    },
    "香港科技大学": {
        "homepage": "https://www.ust.hk",
        "search_terms": [
            "香港科技大学 学生 社团",
            "HKUST student clubs interests",
        ],
    },
}

# 通用校园兴趣标签词库（用于 NLP 提取时的关键词匹配）
UNIVERSAL_CAMPUS_TAGS = [
    # 学术
    "编程", "AI", "数据科学", "机器学习", "研究", "论文",
    # 运动
    "篮球", "足球", "羽毛球", "游泳", "健身", "瑜伽", "跑步", "登山", "帆船",
    # 艺术
    "摄影", "绘画", "设计", "音乐", "吉他", "钢琴", "舞蹈", "戏剧", "电影",
    # 文化
    "读书", "写作", "辩论", "语言", "翻译", "历史", "哲学",
    # 娱乐
    "电竞", "手游", "桌游", "剧本杀", "动漫", "二次元", "K-pop",
    # 社交
    "旅行", "美食", "探店", "咖啡", "志愿服务", "创业",
    # 澳门/香港特色
    "广东话", "葡语", "博彩研究", "酒店管理", "旅游规划",
    "金融", "法律", "国际关系", "环保", "行山",
]


def extract_tags_from_html(html_text, tag_vocabulary=None):
    """
    从 HTML 文本中提取兴趣标签。

    使用正则匹配 + 词库对照。
    日报系统的 "结构化提取" 思路：不依赖单一源，取交集提高准确率。
    """
    if tag_vocabulary is None:
        tag_vocabulary = UNIVERSAL_CAMPUS_TAGS

    # 去除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = re.sub(r'\s+', ' ', text)

    found = Counter()
    for tag in tag_vocabulary:
        count = len(re.findall(re.escape(tag), text))
        if count > 0:
            found[tag] = count

    return found


def search_and_extract(school_name, max_results=20):
    """
    模拟日报系统的搜索流程：
      1. 多关键词搜索
      2. 提取结构化标签
      3. 去重 + 排序

    注意：WebSearch 由 AI agent 执行，此函数返回搜索策略和关键词。
    实际爬取需在 Agent 环境中运行。

    Returns:
        dict with search_strategy, recommended_terms, source_config
    """
    source = PUBLIC_SOURCES.get(school_name)
    if not source:
        return {"error": f"未找到 {school_name} 的信息源配置"}

    strategy = {
        "school": school_name,
        "search_terms": source["search_terms"],
        "homepage": source.get("homepage"),
        "student_orgs": source.get("student_orgs"),
        "target_tags": UNIVERSAL_CAMPUS_TAGS,
        "pipeline": [
            "1. 用以上 search_terms 各执行一次 WebSearch，获取前 10 条结果",
            "2. 对每个结果的 URL 执行 WebFetch，提取页面文本",
            "3. 用 extract_tags_from_html() 提取兴趣标签",
            "4. 合并所有来源的标签，按出现频率排序",
            "5. 取 Top 30 作为该学校的兴趣种子标签",
        ],
        "example_search": {
            "query": source["search_terms"][0],
            "extract_prompt": f"从搜索结果中提取关于{school_name}学生兴趣、社团活动、校园文化的信息。列出所有提到的具体兴趣/活动关键词，用逗号分隔。",
        },
    }

    return strategy


def enrich_school_tags(school_name, new_tags):
    """
    更新学校兴趣标签（爬虫调用此函数写入）。

    日报系统 dedup 思路：避免重复，只追加新标签。
    """
    from questionnaire import SCHOOL_INTEREST_SEEDS

    existing = set(SCHOOL_INTEREST_SEEDS.get(school_name, []))
    added = [t for t in new_tags if t not in existing]

    if school_name not in SCHOOL_INTEREST_SEEDS:
        SCHOOL_INTEREST_SEEDS[school_name] = []

    SCHOOL_INTEREST_SEEDS[school_name].extend(added)

    # 去重并保持顺序
    seen = set()
    deduped = []
    for t in SCHOOL_INTEREST_SEEDS[school_name]:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    SCHOOL_INTEREST_SEEDS[school_name] = deduped

    return {"school": school_name, "added": added, "total_now": len(deduped)}


def get_school_tags(school_name):
    """获取某学校的兴趣标签（供前端显示和冷启动推荐）"""
    from questionnaire import SCHOOL_INTEREST_SEEDS
    return SCHOOL_INTEREST_SEEDS.get(school_name, UNIVERSAL_CAMPUS_TAGS[:20])


def crawl_all_schools_report():
    """
    生成所有学校的搜索策略报告。

    日报系统风格：先出报告，由 Editor Agent 决定是否执行。
    """
    lines = [f"# CampusMatch 学校数据爬取策略报告", f"生成时间: {datetime.now().isoformat()}"]
    lines.append("")

    for school in PUBLIC_SOURCES:
        strategy = search_and_extract(school)
        if "error" in strategy:
            continue
        lines.append(f"## {school}")
        lines.append(f"- 主页: {strategy['homepage']}")
        lines.append(f"- 搜索词: {', '.join(strategy['search_terms'])}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        print(crawl_all_schools_report())
    elif len(sys.argv) > 2 and sys.argv[1] == "--school":
        school = sys.argv[2]
        strategy = search_and_extract(school)
        print(json.dumps(strategy, ensure_ascii=False, indent=2))
    else:
        print("用法:")
        print("  python crawler.py --report        # 生成所有学校的爬取策略报告")
        print("  python crawler.py --school 澳门大学  # 查看某学校的搜索策略")
