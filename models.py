"""CampusMatch 数据库模型 v2"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets, json

db = SQLAlchemy()
EXPRESS_BIO_MIN = 30


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    school = db.Column(db.String(64), nullable=False, index=True)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(64), unique=True)
    verification_sent_at = db.Column(db.DateTime, nullable=True)

    # 基本信息
    name = db.Column(db.String(32))
    gender = db.Column(db.String(16))       # male / female
    # 择偶取向：想匹配的性别 male / female / both（男女不限）
    looking_for = db.Column(db.String(16))
    wechat_id = db.Column(db.String(128))  # 附加联系方式（必填，如微信）；学校邮箱配对成功后也会互见
    bio = db.Column(db.Text)

    # 问卷答案 (JSON)
    # 格式: {"1": 3, "2": 5, "25": ["科幻/奇幻", "悬疑/犯罪"], ...}
    answers_json = db.Column(db.Text)

    # 特征向量 (JSON array of floats)
    feature_vector_json = db.Column(db.Text)

    # 用户标记为"对我很重要"的问题 ID
    important_qids_json = db.Column(db.Text)

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)  # 最近成功登录（用于每日登录限制）
    last_matched_at = db.Column(db.DateTime, nullable=True)
    # 本周预约匹配：ISO 周键，如 "2026-W31"；与当前周相同表示已 opt-in
    opt_in_week = db.Column(db.String(16))
    # 运营补偿：仅在 quota_bonus_week 等于当前 ISO 周时，加在每周上限上
    quota_bonus = db.Column(db.Integer, default=0)
    quota_bonus_week = db.Column(db.String(16))
    # 是否愿意参与跨校（兼容旧字段；与 cross_schools_json 同步：非空列表则为 True）
    allow_cross_school = db.Column(db.Boolean, default=False)
    # 愿意跨配的学校名列表 JSON，如 ["澳门科技大学"]；双向白名单；空=只同校
    cross_schools_json = db.Column(db.Text)
    # 总开关：关则不进匹配池、不能预约/提前揭晓；历史配对仍可看
    open_to_match = db.Column(db.Boolean, default=True)
    # 问卷推演 MBTI 报告 JSON（娱乐向，不参与匹配）
    mbti_json = db.Column(db.Text)
    # 上次「未完成问卷」催填邮件时间（UTC）
    incomplete_nudge_at = db.Column(db.DateTime, nullable=True)
    # full = 39 题问卷；privacy/express = 隐私模式（昵称/性别/取向 + 一段话，微信可选）
    profile_mode = db.Column(db.String(16), default="full")

    tags = db.relationship("UserTag", backref="user", lazy="joined", cascade="all, delete-orphan")

    @property
    def mbti_report(self):
        if not self.mbti_json:
            return None
        try:
            return json.loads(self.mbti_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    @mbti_report.setter
    def mbti_report(self, value):
        if value is None:
            self.mbti_json = None
        else:
            self.mbti_json = json.dumps(value, ensure_ascii=False)

    @property
    def answers(self):
        """返回 {int_qid: value}；JSON 键一律规范为 int，避免匹配时 get(1) 读不到 '1'。"""
        if not self.answers_json:
            return {}
        raw = json.loads(self.answers_json)
        normalized = {}
        for k, v in raw.items():
            try:
                normalized[int(k)] = v
            except (TypeError, ValueError):
                continue
        return normalized

    @answers.setter
    def answers(self, value):
        payload = {}
        for k, v in (value or {}).items():
            try:
                payload[str(int(k))] = v
            except (TypeError, ValueError):
                payload[str(k)] = v
        self.answers_json = json.dumps(payload, ensure_ascii=False)

    @property
    def feature_vector(self):
        if self.feature_vector_json:
            return json.loads(self.feature_vector_json)
        return None

    @feature_vector.setter
    def feature_vector(self, value):
        if value is not None:
            self.feature_vector_json = json.dumps(value)
        else:
            self.feature_vector_json = None

    @property
    def important_qids(self):
        if not self.important_qids_json:
            return set()
        raw = json.loads(self.important_qids_json)
        out = set()
        for x in raw:
            try:
                out.add(int(x))
            except (TypeError, ValueError):
                continue
        return out

    @important_qids.setter
    def important_qids(self, value):
        ids = []
        for x in (value or []):
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        self.important_qids_json = json.dumps(ids)

    def generate_token(self):
        self.verification_token = secrets.token_hex(3).upper()
        self.verification_sent_at = datetime.utcnow()
        return self.verification_token

    def effective_looking_for(self):
        """未设置时按异性默认，兼容旧数据。"""
        if self.looking_for in ("male", "female", "both"):
            return self.looking_for
        if self.gender == "male":
            return "female"
        if self.gender == "female":
            return "male"
        return "both"

    def accepts_gender(self, other_gender):
        pref = self.effective_looking_for()
        if pref == "both":
            return other_gender in ("male", "female")
        return pref == other_gender

    def is_express(self):
        return (self.profile_mode or "full") in ("express", "privacy")

    def questionnaire_completed(self):
        """检查是否完成了问卷"""
        from questionnaire import QUESTIONS

        answers = self.answers
        if not answers:
            return False
        for q in QUESTIONS:
            value = answers.get(q["id"])
            if q.get("optional") or q["type"] == "text":
                continue
            if q["type"] == "scale":
                if value is None:
                    return False
            elif not isinstance(value, list) or not value:
                return False
        return True

    def ready_to_match(self):
        """资料是否齐全（不含是否愿意进池）。"""
        if not (
            self.email_verified
            and self.gender in ("male", "female")
            and self.looking_for in ("male", "female", "both")
            and self.feature_vector
        ):
            return False
        if self.is_express():
            bio = (self.bio or "").strip()
            return bool((self.name or "").strip() and len(bio) >= EXPRESS_BIO_MIN)
        return bool(self.questionnaire_completed() and self.wechat_id)

    def is_open_to_match(self):
        """是否愿意进入匹配池；NULL/缺省视为 True（兼容旧数据）。"""
        return self.open_to_match is not False

    def in_match_pool(self):
        return self.ready_to_match() and self.is_open_to_match()

    def get_cross_schools(self):
        """愿意跨配的学校列表（不含本校）。旧数据仅 allow_cross_school=True 时视为「其它全部学校」。"""
        from config import SCHOOL_DOMAINS

        if self.cross_schools_json:
            try:
                raw = json.loads(self.cross_schools_json)
            except (TypeError, ValueError, json.JSONDecodeError):
                raw = []
            out = []
            for s in raw or []:
                name = str(s).strip()
                if name in SCHOOL_DOMAINS and name != self.school and name not in out:
                    out.append(name)
            return out
        if self.allow_cross_school:
            return [s for s in SCHOOL_DOMAINS.keys() if s != self.school]
        return []

    def set_cross_schools(self, schools):
        from config import SCHOOL_DOMAINS

        out = []
        for s in schools or []:
            name = str(s).strip()
            if name in SCHOOL_DOMAINS and name != self.school and name not in out:
                out.append(name)
        self.cross_schools_json = json.dumps(out, ensure_ascii=False)
        self.allow_cross_school = bool(out)

    def to_dict(self):
        return {
            "id": self.id,
            "school": self.school,
            "email": self.email,
            "email_verified": self.email_verified,
            "name": self.name,
            "gender": self.gender,
            "looking_for": self.effective_looking_for(),
            "wechat_id": self.wechat_id,
            "bio": self.bio,
            "tags": [t.tag for t in self.tags],
            "questionnaire_completed": self.questionnaire_completed(),
            "answers": self.answers,
            "important_qids": list(self.important_qids),
            "opt_in_week": self.opt_in_week,
            "allow_cross_school": bool(self.get_cross_schools()),
            "cross_schools": self.get_cross_schools(),
            "open_to_match": self.is_open_to_match(),
            "mbti": self.mbti_report,
            "profile_mode": "privacy" if self.is_express() else "full",
        }


class UserTag(db.Model):
    __tablename__ = "user_tags"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    tag = db.Column(db.String(32), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "tag", name="uq_user_tag"),
    )


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user1_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    score = db.Column(db.Float, default=0.0)
    mode = db.Column(db.String(16), default="realtime")  # "realtime" | "batch" | "one_to_one"
    insight_json = db.Column(db.Text)  # 匹配理由
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notified = db.Column(db.Boolean, default=False)
    # 配对约 3 天后破冰随访是否已发（每对只发一次）
    icebreaker_followup_sent = db.Column(db.Boolean, default=False)
    # 一对一：同一用户同时只应有 1 条 active=True 的配对；旧 Top-N 多条会被降为 False
    active = db.Column(db.Boolean, default=True, index=True)

    user1 = db.relationship("User", foreign_keys=[user1_id])
    user2 = db.relationship("User", foreign_keys=[user2_id])


class Blocklist(db.Model):
    """不想再匹配的人（双向生效：任一方拉黑则不再配对）。"""
    __tablename__ = "blocklist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    blocked_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    blocked = db.relationship("User", foreign_keys=[blocked_user_id])

    __table_args__ = (
        db.UniqueConstraint("user_id", "blocked_user_id", name="uq_block_pair"),
    )
