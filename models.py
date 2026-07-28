"""CampusMatch 数据库模型 v2"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets, json

db = SQLAlchemy()


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
    wechat_id = db.Column(db.String(32))
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
    last_matched_at = db.Column(db.DateTime, nullable=True)
    # 本周预约匹配：ISO 周键，如 "2026-W31"；与当前周相同表示已 opt-in
    opt_in_week = db.Column(db.String(16))
    # 是否愿意参与跨校匹配（需双方都开，且全局 CROSS_SCHOOL_MATCHING_ENABLED）
    allow_cross_school = db.Column(db.Boolean, default=False)

    tags = db.relationship("UserTag", backref="user", lazy="joined", cascade="all, delete-orphan")

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

    def questionnaire_completed(self):
        """检查是否完成了问卷"""
        return bool(self.answers and len(self.answers) >= 20)  # 至少回答 20 题

    def ready_to_match(self):
        return bool(
            self.email_verified
            and self.questionnaire_completed()
            and self.gender in ("male", "female")
            and self.looking_for in ("male", "female", "both")
            and self.wechat_id
            and self.feature_vector
        )

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
            "allow_cross_school": bool(self.allow_cross_school),
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
