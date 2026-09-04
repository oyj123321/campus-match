"""CampusMatch 种子数据生成器

生成澳大测试用户，用于 MVP 演示匹配效果。
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User
from questionnaire import QUESTIONS, build_feature_vector


SEEDS = [
    # (name, gender, wechat_id, school, email, bio, answers_override)
    ("Alice", "female", "alice_wx", "澳门大学", "alice@um.edu.mo",
     "大三心理学在读，喜欢猫咪和下雨天", {
         1:2,2:4,3:4,4:3,5:2,6:2,7:3,8:1,        # values
         9:4,10:3,11:3,12:2,13:1,14:2,15:1,16:4,  # lifestyle
         17:2,18:["直接说爱与赞美","拥抱牵手等接触"],19:3,20:2,21:2,22:3,23:2,24:4, # emotional
         25:["科幻/奇幻","悬疑/犯罪","动画/二次元"],
         26:["流行","K-Pop/J-Pop"],27:["文学/小说","心理学/自我提升"],
         28:["RPG/开放世界","手游/休闲"],29:2,
         30:["瑜伽/普拉提","跑步/健身"],31:["看展/博物馆","咖啡馆/美食探店"],
         32:["追剧/看电影","和朋友聊天"],
         33:2,34:["一线城市"],35:2,36:2,37:2,38:3,39:2,
     }),

    ("Bob", "male", "bob_wx", "澳门大学", "bob@um.edu.mo",
     "研二工科生，写代码和看动漫是生活必需品", {
         1:2,2:3,3:5,4:4,5:2,6:2,7:3,8:1,
         9:5,10:4,11:2,12:3,13:1,14:3,15:2,16:4,
         17:3,18:["直接说爱与赞美","帮对方做事"],19:4,20:2,21:3,22:4,23:3,24:4,
         25:["科幻/奇幻","动作/冒险","动画/二次元"],
         26:["摇滚/金属","流行"],27:["科幻/奇幻","科技/科普"],
         28:["MOBA（王者/LOL）","RPG/开放世界"],29:3,
         30:["球类运动","跑步/健身"],31:["音乐会/Livehouse","市集/艺术节"],
         32:["打游戏","运动出汗"],
         33:3,34:["一线城市"],35:3,36:3,37:3,38:3,39:3,
     }),

    ("Cathy", "female", "cathy_wx", "澳门大学", "cathy@um.edu.mo",
     "法学院大四，周末喜欢去路环徒步", {
         1:3,2:4,3:3,4:2,5:3,6:3,7:2,8:1,
         9:2,10:2,11:3,12:1,13:1,14:1,15:2,16:5,
         17:1,18:["帮对方做事"],19:2,20:3,21:2,22:2,23:1,24:3,
         25:["悬疑/犯罪","纪录片","爱情/文艺"],
         26:["古典/爵士","民谣/独立"],27:["历史/哲学","文学/小说"],
         28:["不玩游戏","桌游/剧本杀"],29:4,
         30:["徒步/登山","游泳/水上"],31:["看展/博物馆","读书会/讲座"],
         32:["看书/写作","运动出汗"],
         33:2,34:["二线城市"],35:2,36:1,37:2,38:2,39:1,
     }),

    ("David", "male", "david_wx", "澳门大学", "david@um.edu.mo",
     "大二商科，健身房常客，最近在学广东话", {
         1:3,2:3,3:4,4:3,5:3,6:2,7:3,8:2,
         9:3,10:3,11:1,12:3,13:1,14:4,15:3,16:3,
         17:2,18:["帮对方做事","准备礼物惊喜"],19:3,20:2,21:3,22:3,23:2,24:3,
         25:["动作/冒险","喜剧","科幻/奇幻"],
         26:["嘻哈/R&B","流行"],27:["心理学/自我提升","科技/科普"],
         28:["MOBA（王者/LOL）","手游/休闲"],29:4,
         30:["跑步/健身","球类运动"],31:["咖啡馆/美食探店","音乐会/Livehouse"],
         32:["运动出汗","刷社交媒体"],
         33:4,34:["一线城市"],35:2,36:4,37:4,38:4,39:3,
     }),

    ("Emma", "female", "emma_wx", "澳门大学", "emma@um.edu.mo",
     "传理系研一，独立乐队鼓手，喜欢熬夜写歌", {
         1:4,2:5,3:4,4:4,5:4,6:4,7:2,8:2,
         9:5,10:4,11:3,12:4,13:1,14:4,15:3,16:3,
         17:4,18:["帮对方做事","准备礼物惊喜"],19:4,20:2,21:1,22:1,23:3,24:1,
         25:["动画/二次元","恐怖/惊悚","科幻/奇幻"],
         26:["摇滚/金属","电子/EDM","民谣/独立"],27:["文学/小说","漫画/轻小说"],
         28:["RPG/开放世界","独立游戏"],29:2,
         30:["舞蹈","瑜伽/普拉提"],31:["音乐会/Livehouse","市集/艺术节"],
         32:["追剧/看电影","看书/写作"],
         33:4,34:["一线城市","海外"],35:3,36:4,37:2,38:2,39:4,
     }),

    ("Frank", "male", "frank_wx", "澳门大学", "frank@um.edu.mo",
     "教育学院大四，未来的中学老师，喜欢小孩和狗", {
         1:5,2:3,3:2,4:3,5:1,6:1,7:1,8:1,
         9:1,10:2,11:4,12:2,13:1,14:1,15:1,16:4,
         17:1,18:["直接说爱与赞美","拥抱牵手等接触"],19:1,20:2,21:2,22:2,23:1,24:3,
         25:["喜剧","纪录片","爱情/文艺"],
         26:["民谣/独立","什么都听"],27:["历史/哲学","学术/专业书籍"],
         28:["桌游/剧本杀","不玩游戏"],29:5,
         30:["徒步/登山","球类运动"],31:["读书会/讲座","看展/博物馆"],
         32:["看书/写作","和朋友聊天"],
         33:2,34:["三四线城市","小县城"],35:2,36:1,37:3,38:4,39:1,
     }),

    ("Grace", "female", "grace_wx", "澳门大学", "grace@um.edu.mo",
     "金融大三，外表高冷内心沙雕，奶茶重度依赖", {
         1:2,2:3,3:5,4:2,5:3,6:3,7:3,8:1,
         9:3,10:5,11:4,12:3,13:1,14:3,15:4,16:2,
         17:3,18:["帮对方做事","准备礼物惊喜"],19:3,20:3,21:4,22:3,23:2,24:3,
         25:["爱情/文艺","喜剧","科幻/奇幻"],
         26:["K-Pop/J-Pop","流行"],27:["文学/小说","不太看书"],
         28:["手游/休闲","MOBA（王者/LOL）"],29:3,
         30:["不运动","瑜伽/普拉提"],31:["咖啡馆/美食探店","市集/艺术节"],
         32:["刷社交媒体","追剧/看电影"],
         33:3,34:["一线城市"],35:3,36:3,37:3,38:3,39:3,
     }),

    ("Henry", "male", "henry_wx", "澳门大学", "henry@um.edu.mo",
     "计算机大四，对AI创业狂热，喜欢攀岩和象棋", {
         1:1,2:4,3:5,4:2,5:4,6:4,7:4,8:1,
         9:2,10:3,11:2,12:4,13:1,14:2,15:3,16:3,
         17:1,18:["帮对方做事","准备礼物惊喜"],19:5,20:2,21:1,22:4,23:4,24:3,
         25:["科幻/奇幻","纪录片","动作/冒险"],
         26:["古典/爵士","电子/EDM"],27:["科技/科普","科幻/奇幻"],
         28:["独立游戏","主机/PC大作"],29:4,
         30:["极限运动","跑步/健身"],31:["读书会/讲座","看展/博物馆"],
         32:["看书/写作","打游戏"],
         33:2,34:["一线城市","海外"],35:4,36:4,37:2,38:2,39:4,
     }),

    ("Ivy", "female", "ivy_wx", "澳门科技大学", "ivy@must.edu.mo",
     "设计学大二，社交媒体重度用户，探店达人", {
         1:3,2:5,3:4,4:4,5:3,6:5,7:2,8:2,
         9:4,10:3,11:4,12:3,13:1,14:3,15:3,16:3,
         17:3,18:["直接说爱与赞美","准备礼物惊喜"],19:2,20:4,21:4,22:1,23:1,24:2,
         25:["爱情/文艺","动画/二次元","喜剧"],
         26:["K-Pop/J-Pop","流行"],27:["漫画/轻小说","文学/小说"],
         28:["手游/休闲","不玩游戏"],29:3,
         30:["舞蹈","不运动"],31:["咖啡馆/美食探店","市集/艺术节"],
         32:["刷社交媒体","追剧/看电影"],
         33:4,34:["一线城市"],35:2,36:3,37:2,38:4,39:3,
     }),

    ("Jack", "male", "jack_wx", "澳门科技大学", "jack@must.edu.mo",
     "商科大三，喜欢探店和羽毛球，开了跨校想认识澳大同学", {
         1:2,2:4,3:4,4:3,5:2,6:2,7:3,8:1,
         9:3,10:3,11:2,12:2,13:1,14:2,15:2,16:3,
         17:2,18:["拥抱牵手等接触","帮对方做事"],19:3,20:2,21:2,22:3,23:2,24:3,
         25:["科幻/奇幻","喜剧","动画/二次元"],
         26:["流行","K-Pop/J-Pop"],27:["科技/科普","不太看书"],
         28:["手游/休闲","MOBA（王者/LOL）"],29:3,
         30:["球类运动","跑步/健身"],31:["咖啡馆/美食探店","市集/艺术节"],
         32:["打游戏","和朋友聊天"],
         33:3,34:["一线城市"],35:2,36:3,37:2,38:3,39:2,
     }),
]


def _degree_for(bio):
    if any(k in bio for k in ("博士", "博一", "博二", "博三")):
        return "doctorate"
    if "研" in bio:
        return "master"
    return "bachelor"


# Alice（本科）与 Bob（硕士）互开跨学历，避免演示配对被学历切断
CROSS_DEGREE_EMAILS = {"alice@um.edu.mo", "bob@um.edu.mo"}


def seed(refresh=False):
    with app.app_context():
        db.create_all()

        count = 0
        refreshed = 0
        for name, gender, wechat, school, email, bio, answers in SEEDS:
            existing = User.query.filter_by(email=email).first()
            # 演示数据默认异性取向；个别账号可在此覆盖以测同性匹配
            looking_for = "female" if gender == "male" else "male"
            if email == "emma@um.edu.mo":
                looking_for = "both"
            # 跨校演示：Alice(澳大) + Ivy(科大) 都开跨校
            allow_cross = email in ("alice@um.edu.mo", "ivy@must.edu.mo", "jack@must.edu.mo")
            education = _degree_for(bio)
            allow_cross_degree = email in CROSS_DEGREE_EMAILS

            # 为缺失 scale 题填默认值
            full_answers = {}
            for q in QUESTIONS:
                qid = q["id"]
                if qid in answers:
                    full_answers[qid] = answers[qid]
                elif q["type"] == "scale":
                    full_answers[qid] = 3  # 默认中间值

            # 清洗 multi 选项（防止历史脏值）
            for q in QUESTIONS:
                if q["type"] != "multi":
                    continue
                qid = q["id"]
                if qid not in full_answers:
                    continue
                allowed = set(q["options"])
                clean = list(dict.fromkeys(
                    x for x in (full_answers[qid] or []) if x in allowed
                ))
                exclusive = set(q.get("exclusive_options") or [])
                chosen_exclusive = next((x for x in clean if x in exclusive), None)
                full_answers[qid] = [chosen_exclusive] if chosen_exclusive else clean

            vec, _ = build_feature_vector(full_answers)

            if existing:
                if not refresh:
                    print(f"  SKIP: {name} already exists")
                    continue
                existing.name = name
                existing.gender = gender
                existing.looking_for = looking_for
                existing.wechat_id = wechat
                existing.school = school
                existing.bio = bio
                existing.email_verified = True
                existing.allow_cross_school = allow_cross
                existing.education_level = education
                existing.allow_cross_degree = allow_cross_degree
                existing.answers = full_answers
                existing.feature_vector = vec
                refreshed += 1
                print(f"  REFRESH: {name} ({gender}->{looking_for}) @ {school} edu={education} cross={allow_cross} crossDeg={allow_cross_degree}")
                continue

            user = User(
                email=email,
                school=school,
                email_verified=True,
                name=name,
                gender=gender,
                looking_for=looking_for,
                wechat_id=wechat,
                bio=bio,
                allow_cross_school=allow_cross,
                education_level=education,
                allow_cross_degree=allow_cross_degree,
            )
            user.answers = full_answers
            user.feature_vector = vec
            db.session.add(user)
            count += 1
            print(f"  ADD: {name} ({gender}->{looking_for}) @ {school} edu={education} cross={allow_cross} crossDeg={allow_cross_degree}")

        db.session.commit()
        print(f"\nSeeded {count} users, refreshed {refreshed} (skipped {len(SEEDS) - count - refreshed})")


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    seed(refresh=refresh)
