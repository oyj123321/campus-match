"""CampusMatch 配置 — 澳门大学为基础，逐步扩展香港"""

import os

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "campus-match-dev-secret-key-change-in-production")
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///campus_match.db")

# 邮件配置
MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false").lower() == "true"
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.qq.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@campus-match.local")

# ============================================================
# 高校邮箱域名 — 扩展路径：
#   澳门大学 → 澳门科技/理工/旅游 → 香港 → 深圳/珠海
# ============================================================
SCHOOL_DOMAINS = {
    # ---- 澳门 ----
    "澳门大学":       ["um.edu.mo", "umac.mo"],
    "澳门科技大学":   ["must.edu.mo"],
    "澳门理工大学":   ["mpu.edu.mo"],
    "澳门旅游大学":   ["iftm.edu.mo"],
    "澳门城市大学":   ["cityu.edu.mo"],

    # ---- 香港（后续开放）----
    # "香港大学":       ["hku.hk", "connect.hku.hk"],
    # "香港中文大学":   ["link.cuhk.edu.hk", "cuhk.edu.hk"],
    # "香港科技大学":   ["ust.hk", "connect.ust.hk"],
    # "香港理工大学":   ["polyu.edu.hk", "connect.polyu.hk"],
    # "香港城市大学":   ["cityu.edu.hk"],
    # "香港浸会大学":   ["hkbu.edu.hk"],

    # ---- 上海（参考案例，已验证可行）----
    "上海交通大学":   ["sjtu.edu.cn"],
    "复旦大学":       ["fudan.edu.cn"],
    "同济大学":       ["tongji.edu.cn"],
    "华东师范大学":   ["ecnu.edu.cn"],
}

# 匹配配置
MATCH_MODE = os.environ.get("MATCH_MODE", "realtime")  # "realtime" | "batch"
MATCH_TOP_N = 5              # 实时模式：返回前 N 名
MATCH_MIN_SCORE = 0.15       # 最低余弦相似度阈值
BATCH_MATCH_DAY = 1          # 批量匹配：每周几执行（1=周二）
BATCH_MATCH_HOUR = 21        # 批量匹配：几点执行（21=晚9点）
MATCH_DELAY_SECONDS = 0      # 匹配延迟（秒），防止瞬时并发

# 验证码
VERIFICATION_EXPIRE_SECONDS = 600  # 10 分钟
