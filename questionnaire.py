"""
CampusMatch 深度问卷系统

参考 SJTU Date 的 65 题设计，提炼为 32 题四维度问卷：
  1. 核心价值观 (8题) — Q1-Q8
  2. 生活习惯   (8题) — Q9-Q16
  3. 情感风格   (8题) — Q17-Q24
  4. 兴趣爱好   (8题) — Q25-Q32

输出 80+ 维特征向量，用于余弦相似度匹配。
"""

QUESTIONS = [
    # ===== 维度1: 核心价值观 =====
    {
        "id": 1,
        "dimension": "values",
        "text": "你的人生追求更偏向哪边？",
        "type": "scale",  # 1-5 Likert
        "left": "事业成就",
        "right": "家庭幸福",
        "dealbreaker": False,
    },
    {
        "id": 2,
        "dimension": "values",
        "text": "对社会议题的态度？",
        "type": "scale",
        "left": "保守传统",
        "right": "开放进步",
        "dealbreaker": False,
    },
    {
        "id": 3,
        "dimension": "values",
        "text": "宗教信仰在你生活中的重要性？",
        "type": "scale",
        "left": "非常重要",
        "right": "完全不重要",
        "dealbreaker": False,
    },
    {
        "id": 4,
        "dimension": "values",
        "text": "收入如何分配？",
        "type": "scale",
        "left": "储蓄为主，未雨绸缪",
        "right": "享受当下，及时行乐",
        "dealbreaker": False,
    },
    {
        "id": 5,
        "dimension": "values",
        "text": "对婚姻的看法？",
        "type": "scale",
        "left": "人生必需",
        "right": "可有可无",
        "dealbreaker": True,  # 一票否决
    },
    {
        "id": 6,
        "dimension": "values",
        "text": "是否想要孩子？",
        "type": "scale",
        "left": "一定要",
        "right": "一定不要",
        "dealbreaker": True,
    },
    {
        "id": 7,
        "dimension": "values",
        "text": "朋友和恋人的时间分配？",
        "type": "scale",
        "left": "恋人为重",
        "right": "朋友同样重要",
        "dealbreaker": False,
    },
    {
        "id": 8,
        "dimension": "values",
        "text": "对精神/肉体出轨的态度？",
        "type": "scale",
        "left": "绝对不可原谅",
        "right": "可以理解/沟通解决",
        "dealbreaker": True,
    },

    # ===== 维度2: 生活习惯 =====
    {
        "id": 9,
        "dimension": "lifestyle",
        "text": "你的作息时间？",
        "type": "scale",
        "left": "早睡早起（22点睡6点起）",
        "right": "夜猫子（凌晨2点后睡）",
        "dealbreaker": False,
    },
    {
        "id": 10,
        "dimension": "lifestyle",
        "text": "饮食偏好？",
        "type": "scale",
        "left": "清淡健康",
        "right": "无辣不欢/重口味",
        "dealbreaker": False,
    },
    {
        "id": 11,
        "dimension": "lifestyle",
        "text": "运动频率？",
        "type": "scale",
        "left": "每天坚持",
        "right": "几乎不运动",
        "dealbreaker": False,
    },
    {
        "id": 12,
        "dimension": "lifestyle",
        "text": "居住空间的整洁程度？",
        "type": "scale",
        "left": "一尘不染，物品归位",
        "right": "随意就好，不拘小节",
        "dealbreaker": False,
    },
    {
        "id": 13,
        "dimension": "lifestyle",
        "text": "抽烟习惯？",
        "type": "scale",
        "left": "从不抽烟",
        "right": "经常抽烟",
        "dealbreaker": True,
    },
    {
        "id": 14,
        "dimension": "lifestyle",
        "text": "喝酒习惯？",
        "type": "scale",
        "left": "滴酒不沾",
        "right": "经常小酌/聚会喝酒",
        "dealbreaker": False,
    },
    {
        "id": 15,
        "dimension": "lifestyle",
        "text": "对宠物的态度？",
        "type": "scale",
        "left": "非常喜欢，一定要养",
        "right": "不太喜欢/过敏/不养",
        "dealbreaker": False,
    },
    {
        "id": 16,
        "dimension": "lifestyle",
        "text": "旅行风格？",
        "type": "scale",
        "left": "精致规划，打卡清单",
        "right": "随性流浪，走到哪算哪",
        "dealbreaker": False,
    },

    # ===== 维度3: 情感风格 =====
    {
        "id": 17,
        "dimension": "emotional",
        "text": "吵架时你通常怎么做？",
        "type": "scale",
        "left": "立刻冷静沟通解决",
        "right": "需要时间冷静/先回避",
        "dealbreaker": False,
    },
    {
        "id": 18,
        "dimension": "emotional",
        "text": "你更偏向如何表达爱意？",
        "type": "scale",
        "left": "言语表达+身体接触",
        "right": "实际行动+惊喜礼物",
        "dealbreaker": False,
    },
    {
        "id": 19,
        "dimension": "emotional",
        "text": "你需要多少独处时间？",
        "type": "scale",
        "left": "几乎不需要，喜欢腻在一起",
        "right": "需要大量独处空间",
        "dealbreaker": False,
    },
    {
        "id": 20,
        "dimension": "emotional",
        "text": "对伴侣与异性正常社交的看法？",
        "type": "scale",
        "left": "完全不介意，充分信任",
        "right": "会比较介意/需要边界",
        "dealbreaker": False,
    },
    {
        "id": 21,
        "dimension": "emotional",
        "text": "你的吃醋频率？",
        "type": "scale",
        "left": "几乎不吃醋",
        "right": "比较容易吃醋",
        "dealbreaker": False,
    },
    {
        "id": 22,
        "dimension": "emotional",
        "text": "浪漫 vs 务实？",
        "type": "scale",
        "left": "极度浪漫，仪式感很重要",
        "right": "极度务实，过日子才重要",
        "dealbreaker": False,
    },
    {
        "id": 23,
        "dimension": "emotional",
        "text": "期望每天和伴侣沟通的频率？",
        "type": "scale",
        "left": "时刻保持联系，分享日常",
        "right": "有事再说，不必天天聊",
        "dealbreaker": False,
    },
    {
        "id": 24,
        "dimension": "emotional",
        "text": "对前任的态度？",
        "type": "scale",
        "left": "可以做朋友",
        "right": "最好彻底删除/不联系",
        "dealbreaker": False,
    },

    # ===== 维度4: 兴趣爱好 =====
    {
        "id": 25,
        "dimension": "interests",
        "text": "最喜欢的影视类型？（可多选）",
        "type": "multi",
        "options": ["科幻/奇幻", "悬疑/犯罪", "爱情/文艺", "喜剧", "动作/冒险", "动画/二次元", "纪录片", "恐怖/惊悚"],
    },
    {
        "id": 26,
        "dimension": "interests",
        "text": "音乐品味？（可多选）",
        "type": "multi",
        "options": ["流行", "摇滚/金属", "嘻哈/R&B", "电子/EDM", "古典/爵士", "民谣/独立", "K-Pop/J-Pop", "什么都听"],
    },
    {
        "id": 27,
        "dimension": "interests",
        "text": "阅读偏好？（可多选）",
        "type": "multi",
        "options": ["文学/小说", "科幻/奇幻", "历史/哲学", "心理学/自我提升", "科技/科普", "漫画/轻小说", "不太看书", "学术/专业书籍"],
    },
    {
        "id": 28,
        "dimension": "interests",
        "text": "游戏类型？（可多选）",
        "type": "multi",
        "options": ["MOBA（王者/LOL）", "FPS/射击", "RPG/开放世界", "独立游戏", "手游/休闲", "桌游/剧本杀", "不玩游戏", "主机/PC大作"],
    },
    {
        "id": 29,
        "dimension": "interests",
        "text": "户外 vs 室内？",
        "type": "scale",
        "left": "户外探险家，周末必须出去",
        "right": "宅家达人，在家最舒服",
        "dealbreaker": False,
    },
    {
        "id": 30,
        "dimension": "interests",
        "text": "运动项目偏好？（可多选）",
        "type": "multi",
        "options": ["跑步/健身", "球类运动", "游泳/水上", "瑜伽/普拉提", "极限运动", "舞蹈", "不运动", "徒步/登山"],
    },
    {
        "id": 31,
        "dimension": "interests",
        "text": "文化活动兴趣？（可多选）",
        "type": "multi",
        "options": ["看展/博物馆", "音乐会/Livehouse", "话剧/音乐剧", "电影/影展", "读书会/讲座", "咖啡馆/美食探店", "不太参加", "市集/艺术节"],
    },
    {
        "id": 32,
        "dimension": "interests",
        "text": "你通常用什么方式放松？（可多选）",
        "type": "multi",
        "options": ["追剧/看电影", "打游戏", "运动出汗", "看书/写作", "和朋友聊天", "睡觉", "做饭/烘焙", "刷社交媒体"],
    },
]


def _norm_answers(answers):
    """兼容 int / str 题号键。"""
    if not answers:
        return {}
    out = {}
    for k, v in answers.items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            continue
    return out


def _norm_important_ids(important_ids):
    if not important_ids:
        return set()
    out = set()
    for x in important_ids:
        try:
            out.add(int(x))
        except (TypeError, ValueError):
            continue
    return out


def build_feature_vector(answers, important_ids=None):
    """
    将用户答案转换为特征向量。

    Args:
        answers: dict {question_id: answer_value}
                 scale 题: answer_value 是 1-5 的整数
                 multi 题: answer_value 是 ["选项A", "选项C"] 的列表
        important_ids: set of question_ids 用户标记为"对我很重要"

    Returns:
        vector: list of float, 归一化的特征向量
        dimension_names: list of str, 每个维度的名称（用于调试和可解释性）
    """
    answers = _norm_answers(answers)
    important_ids = _norm_important_ids(important_ids)

    vector = []
    dim_names = []

    for q in QUESTIONS:
        qid = q["id"]
        weight = 2.0 if qid in important_ids else 1.0

        if q["type"] == "scale":
            val = answers.get(qid, 3)  # 默认中间值
            try:
                val = int(val)
            except (TypeError, ValueError):
                val = 3
            val = max(1, min(5, val))
            # 归一化到 [0, 1]
            normalized = (float(val) - 1) / 4.0
            vector.append(normalized * weight)
            dim_names.append(f"Q{qid}_{q['dimension']}")

        elif q["type"] == "multi":
            selected = set(answers.get(qid, []) or [])
            for opt in q["options"]:
                val = 1.0 if opt in selected else 0.0
                vector.append(val * weight)
                dim_names.append(f"Q{qid}_{opt}")

    return vector, dim_names


def cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度 [0, 1]"""
    if len(vec1) != len(vec2):
        raise ValueError(f"向量维度不匹配: {len(vec1)} vs {len(vec2)}")

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def check_dealbreakers(answers1, answers2, threshold=0.6):
    """
    检查一票否决条件。

    对标记为 dealbreaker 的 scale 题，如果两人的答案差距超过
    threshold（即归一化后差距 > 0.6，相当于原始 scale 差 ≥ 3），
    则返回所有触发否决的问题。

    Returns:
        list of question texts that triggered dealbreaker
    """
    answers1 = _norm_answers(answers1)
    answers2 = _norm_answers(answers2)
    triggered = []

    for q in QUESTIONS:
        if not q.get("dealbreaker"):
            continue
        if q["type"] != "scale":
            continue

        qid = q["id"]
        try:
            v1 = float(answers1.get(qid, 3))
            v2 = float(answers2.get(qid, 3))
        except (TypeError, ValueError):
            continue

        # scale 差 ≥ 3 → 否决
        if abs(v1 - v2) >= 3:
            triggered.append(q["text"])

    return triggered


def get_compatibility_insight(user_vec, match_vec, answers, match_answers):
    """
    生成匹配理由——找出相似度最高和最低的维度，给出可读解释。

    Returns:
        dict with 'strengths' (共同点) and 'differences' (需要注意的差异)
    """
    answers = _norm_answers(answers)
    match_answers = _norm_answers(match_answers)
    strengths = []
    differences = []

    for q in QUESTIONS:
        qid = q["id"]
        if q["type"] == "scale":
            try:
                v1 = float(answers.get(qid, 3))
                v2 = float(match_answers.get(qid, 3))
            except (TypeError, ValueError):
                continue
            diff = abs(v1 - v2)
            if diff <= 1:
                strengths.append(f"「{q['text']}」观点相近")
            elif diff >= 3:
                differences.append(f"「{q['text']}」差异较大")
        elif q["type"] == "multi":
            s1 = set(answers.get(qid, []) or [])
            s2 = set(match_answers.get(qid, []) or [])
            common = s1 & s2
            if len(common) >= 2:
                strengths.append(f"「{q['text']}」都喜欢：{'、'.join(list(common)[:3])}")

    return {
        "strengths": strengths[:5],    # top 5
        "differences": differences[:3],  # top 3
        "total_strengths": len(strengths),
        "total_differences": len(differences),
    }


# ---- 学校兴趣标签数据库（爬虫填充 + 手工维护）----
# 可被 crawler.py 更新
SCHOOL_INTEREST_SEEDS = {
    "澳门大学": [
        "学术研究", "社团活动", "广东话", "葡语", "澳门美食",
        "旅行", "摄影", "编程", "金融", "创业",
        "桌游", "篮球", "游泳", "音乐会", "看展",
    ],
    "澳门科技大学": [
        "编程", "设计", "创业", "电竞", "摄影",
        "旅行", "美食", "电影", "健身", "舞蹈",
        "商科", "AI", "区块链", "音乐", "动漫",
    ],
    "澳门理工大学": [
        "翻译", "教育", "社工", "编程", "设计",
        "音乐", "运动", "读书", "旅行", "志愿服务",
    ],
    "澳门旅游大学": [
        "酒店管理", "旅游规划", "美食", "文化研究",
        "语言学习", "摄影", "户外运动", "社交活动",
    ],
    "香港大学": [
        "学术研究", "辩论", "编程", "金融", "法律",
        "音乐", "登山", "帆船", "创业", "国际关系",
    ],
    "香港中文大学": [
        "文学", "哲学", "社会学", "科技创新", "创业",
        "音乐", "戏剧", "行山", "环保", "志愿服务",
    ],
    "香港科技大学": [
        "编程", "AI", "机器人", "创业", "金融科技",
        "帆船", "登山", "摄影", "音乐", "电竞",
    ],
}
