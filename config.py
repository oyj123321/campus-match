"""CampusMatch 配置 — 澳门大学为基础，逐步扩展香港"""

import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 .env 文件（不依赖第三方库；.env 优先于残留环境变量，避免旧 serveo URL 污染）
_ENV_FILE = os.path.join(BASE_DIR, ".env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key:
                    os.environ[key] = val

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "campus-match-dev-secret-key-change-in-production")
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'campus_match.db')}"
)

# 公网地址（serveo 隧道自动设置，也可手动指定）
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://127.0.0.1:5000")

# 邮件配置 — MAIL_PROVIDER=smtp（QQ）或 resend
MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false").lower() == "true"
MAIL_PROVIDER = os.environ.get("MAIL_PROVIDER", "smtp").strip().lower()  # smtp | resend
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.qq.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")       # 你的 QQ 邮箱地址
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")       # QQ 邮箱 SMTP 授权码（不是 QQ 密码！）
MAIL_FROM = os.environ.get("MAIL_FROM", MAIL_USERNAME or "noreply@campus-match.local")
# Resend：https://resend.com → API Keys；发信域名需先在 Resend 验证
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")


def _extract_email(raw: str) -> str:
    """从 `Name <a@b.com>` 或纯地址中取出邮箱。"""
    import re

    s = (raw or "").strip()
    m = re.search(r"<([^>]+)>", s)
    if m:
        return m.group(1).strip()
    if "@" in s and " " not in s:
        return s
    m2 = re.search(r"[\w.+\-]+@[\w.\-]+\.\w+", s)
    return m2.group(0) if m2 else s


# 运营联系 / 删号申请（可写在 .env；与发信 MAIL_FROM 分开）
CONTACT_EMAIL = (
    os.environ.get("CONTACT_EMAIL")
    or "y283664393@gmail.com"
)


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
}

# 匹配配置
# one_to_one（默认）：点「开始匹配」只配对 1 人（当前池子里得分最高且双向取向兼容）
# top_n：旧行为，一次返回多人（调试用，设 MATCH_MODE=top_n）
MATCH_MODE = os.environ.get("MATCH_MODE", "one_to_one")  # one_to_one | top_n | batch
MATCH_TOP_N = int(os.environ.get("MATCH_TOP_N", "1"))  # top_n 模式返回人数；one_to_one 强制为 1
MATCH_MIN_SCORE = float(os.environ.get("MATCH_MIN_SCORE", "0.15"))  # 契合度门槛，默认 15%（不对用户展示分数）
BATCH_MATCH_DAY = int(os.environ.get("BATCH_MATCH_DAY", "1"))   # 0=周一 … 1=周二
BATCH_MATCH_HOUR = int(os.environ.get("BATCH_MATCH_HOUR", "21"))  # 晚 9 点
MATCH_DELAY_SECONDS = 0
# 运营额度：每人每周最多参与 1 次新匹配（发起或被配都算）
MATCH_WEEKLY_NEW_LIMIT = int(os.environ.get("MATCH_WEEKLY_NEW_LIMIT", "1"))
MATCH_COOLDOWN_HOURS = int(os.environ.get("MATCH_COOLDOWN_HOURS", "12"))
BATCH_SCHEDULER_ENABLED = os.environ.get("BATCH_SCHEDULER_ENABLED", "false").lower() == "true"
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")
# 揭晓仪式：需本周 opt-in 才进批量池；冷启动仍可开即时匹配
REVEAL_REQUIRE_OPT_IN = os.environ.get("REVEAL_REQUIRE_OPT_IN", "true").lower() == "true"
INSTANT_MATCH_ENABLED = os.environ.get("INSTANT_MATCH_ENABLED", "true").lower() == "true"
# 跨校总闸：true 时，允许按「双方互相勾选对方学校」做跨校配对
CROSS_SCHOOL_MATCHING_ENABLED = os.environ.get("CROSS_SCHOOL_MATCHING_ENABLED", "true").lower() == "true"
# 配对成功后第 N 天发破冰随访（催打招呼；避开整周揭晓日）
ICEBREAKER_FOLLOWUP_DAYS = int(os.environ.get("ICEBREAKER_FOLLOWUP_DAYS", "3"))

# 验证码
VERIFICATION_EXPIRE_SECONDS = 600  # 10 分钟
# 注册/重发验证码限流（同一邮箱）
REGISTER_RATE_LIMIT = int(os.environ.get("REGISTER_RATE_LIMIT", "5"))  # 窗口内最多次数
REGISTER_RATE_WINDOW = int(os.environ.get("REGISTER_RATE_WINDOW", "3600"))  # 秒

# weekday 显示名（供前端）
WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
