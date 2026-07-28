"""CampusMatch 配置 — 澳门大学为基础，逐步扩展香港"""

import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 .env 文件（不依赖第三方库）
_ENV_FILE = os.path.join(BASE_DIR, ".env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key and key not in os.environ:
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

# 邮件配置 — 设置 MAIL_ENABLED=true 并填入 QQ 邮箱 SMTP 授权码即可
MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false").lower() == "true"
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.qq.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")       # 你的 QQ 邮箱地址
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")       # QQ 邮箱 SMTP 授权码（不是 QQ 密码！）
MAIL_FROM = os.environ.get("MAIL_FROM", MAIL_USERNAME or "noreply@campus-match.local")

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
# one_to_one（默认）：点「开始匹配」只配对 1 人（当前池子里得分最高且双向取向兼容）
# top_n：旧行为，一次返回多人（调试用，设 MATCH_MODE=top_n）
MATCH_MODE = os.environ.get("MATCH_MODE", "one_to_one")  # one_to_one | top_n | batch
MATCH_TOP_N = int(os.environ.get("MATCH_TOP_N", "1"))  # top_n 模式返回人数；one_to_one 强制为 1
MATCH_MIN_SCORE = float(os.environ.get("MATCH_MIN_SCORE", "0.15"))
BATCH_MATCH_DAY = int(os.environ.get("BATCH_MATCH_DAY", "1"))   # 0=周一 … 1=周二
BATCH_MATCH_HOUR = int(os.environ.get("BATCH_MATCH_HOUR", "21"))  # 晚 9 点
MATCH_DELAY_SECONDS = 0
# 运营额度：一对一产品默认每周 1 个新匹配
MATCH_WEEKLY_NEW_LIMIT = int(os.environ.get("MATCH_WEEKLY_NEW_LIMIT", "1"))
MATCH_COOLDOWN_HOURS = int(os.environ.get("MATCH_COOLDOWN_HOURS", "12"))
BATCH_SCHEDULER_ENABLED = os.environ.get("BATCH_SCHEDULER_ENABLED", "false").lower() == "true"
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")

# 验证码
VERIFICATION_EXPIRE_SECONDS = 600  # 10 分钟
# 注册/重发验证码限流（同一邮箱）
REGISTER_RATE_LIMIT = int(os.environ.get("REGISTER_RATE_LIMIT", "5"))  # 窗口内最多次数
REGISTER_RATE_WINDOW = int(os.environ.get("REGISTER_RATE_WINDOW", "3600"))  # 秒

# weekday 显示名（供前端）
WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
