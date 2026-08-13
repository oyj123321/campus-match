"""本地纯函数验证：Top-1 硬性底线冲突时应落到 Top-2。"""
from types import SimpleNamespace

from matcher import pick_without_dealbreaker, greedy_match_all, batch_match_school
from questionnaire import check_dealbreakers


def _user(uid, answers, vec=(1.0, 0.0), gender="female", looking="male"):
    u = SimpleNamespace(
        id=uid,
        answers=answers,
        feature_vector=list(vec),
        gender=gender,
        looking_for=looking,
    )
    u.accepts_gender = lambda g, lf=looking: (
        True if lf == "both" else g == lf
    )
    u.effective_looking_for = lambda lf=looking: lf
    return u


# Q13 吸烟：差距 ≥3 触发。me=1（很反感），top1=5（无所谓/吸烟）冲突；top2=2 无冲突
me = _user(1, {13: 1}, vec=(1.0, 0.0), gender="female", looking="male")
top1 = _user(63, {13: 5}, vec=(0.99, 0.1), gender="male", looking="female")  # ~高相似
top2 = _user(62, {13: 2}, vec=(0.95, 0.2), gender="male", looking="female")  # 略低

assert check_dealbreakers(me.answers, top1.answers), "top1 应冲突"
assert not check_dealbreakers(me.answers, top2.answers), "top2 应无冲突"

scored = [(top1, 0.63), (top2, 0.62)]  # 模拟孙夕蘅 case
kept, skipped = pick_without_dealbreaker(me, scored, max_n=1)
assert skipped == 1
assert len(kept) == 1 and kept[0][0].id == 62 and kept[0][1] == 0.62
print("OK pick_without_dealbreaker: skip 63 -> keep 62")

# 全冲突
kept2, skipped2 = pick_without_dealbreaker(me, [(top1, 0.63)], max_n=1)
assert kept2 == [] and skipped2 == 1
print("OK all dealbreaker -> empty")

# batch/greedy：冲突边不进配对
a = _user(10, {13: 1}, vec=(1.0, 0.0), gender="female", looking="male")
b_bad = _user(11, {13: 5}, vec=(0.99, 0.05), gender="male", looking="female")
b_ok = _user(12, {13: 1}, vec=(0.9, 0.1), gender="male", looking="female")
pairs = greedy_match_all([a, b_bad, b_ok], min_score=0.1, require_orientation=True)
ids = {(p[0].id, p[1].id) for p in pairs} | {(p[1].id, p[0].id) for p in pairs}
assert (10, 11) not in ids and (11, 10) not in ids
assert (10, 12) in ids or (12, 10) in ids
print("OK greedy_match_all skips dealbreaker edge")

pairs2 = batch_match_school([a, b_bad, b_ok], filter_same_gender=True)
# 匈牙利/贪心结果里不应出现 a-b_bad 且分数>0 的硬配
for u1, u2, s in pairs2:
    if {u1.id, u2.id} == {10, 11}:
        assert s <= 0 or check_dealbreakers(u1.answers, u2.answers)
        raise AssertionError("batch 不应产出吸烟冲突对")
print("OK batch_match_school avoids dealbreaker pair")
print("ALL PASSED")
