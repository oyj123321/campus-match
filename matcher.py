"""
CampusMatch 匹配引擎 v2

两种模式：
  1. 实时匹配 (real-time) — 余弦相似度 Top-N，适合开发/测试
  2. 定时匹配 (batch) — 匈牙利算法全局最优，每人只匹配一个对象
     参考 SJTU Date 每周二晚 9 点执行

算法选择：
  - 异性匹配 → 二部图 (bipartite)，匈牙利算法 O(n³)
  - 同性/不限 → 一般图最大权匹配，用贪心近似
"""

import math
from itertools import combinations


def _matching_text(user):
    from questionnaire import get_open_letter

    parts = []
    bio = (getattr(user, "bio", None) or "").strip()
    if bio:
        parts.append(bio)
    letter = get_open_letter(getattr(user, "answers", None) or {})
    if letter:
        parts.append(letter)
    return "\n".join(parts)


def text_similarity(a, b):
    """中英都可用的 bigram Jaccard，映射到约 0.18–1，避免隐私用户分过低进不了门槛。"""
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if len(a) < 2 or len(b) < 2:
        return 0.18

    def grams(s):
        g = {s[i : i + 2] for i in range(len(s) - 1)}
        for tok in s.replace("，", " ").replace(",", " ").split():
            if len(tok) >= 2:
                g.add(tok)
        return g

    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.18
    j = len(ga & gb) / max(1, len(ga | gb))
    return round(0.18 + 0.82 * j, 4)


def _is_express_user(u):
    fn = getattr(u, "is_express", None)
    if callable(fn):
        return bool(fn())
    return (getattr(u, "profile_mode", None) or "full") in ("express", "privacy")


def pair_score(user_a, user_b):
    """问卷用户走余弦；任一方隐私模式则混入自我介绍文本相似。"""
    c = cosine_similarity(
        getattr(user_a, "feature_vector", None),
        getattr(user_b, "feature_vector", None),
    )
    ea, eb = _is_express_user(user_a), _is_express_user(user_b)
    if not ea and not eb:
        return c
    t = text_similarity(_matching_text(user_a), _matching_text(user_b))
    if ea and eb:
        return round(0.25 * c + 0.75 * t, 4)
    return round(0.45 * c + 0.55 * t, 4)


def cosine_similarity(vec1, vec2):
    """余弦相似度 [0, 1]。维数不一致时返回 0（需双方重交问卷对齐）。"""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def orientation_compatible(user_a, user_b):
    """双向择偶取向兼容：双方都愿意匹配对方的性别。"""
    if not hasattr(user_a, "accepts_gender") or not hasattr(user_b, "accepts_gender"):
        return True
    if not user_a.gender or not user_b.gender:
        return False
    return user_a.accepts_gender(user_b.gender) and user_b.accepts_gender(user_a.gender)


def _dealbreaker_conflict(user_a, user_b):
    """硬性底线冲突。任一方隐私模式则不否决（含从问卷改过来、旧答案仍在库里）。"""
    if _is_express_user(user_a) or _is_express_user(user_b):
        return False
    from questionnaire import check_dealbreakers
    a = getattr(user_a, "answers", None) or {}
    b = getattr(user_b, "answers", None) or {}
    return bool(check_dealbreakers(a, b))


def pick_without_dealbreaker(user, scored_pairs, max_n=1):
    """
    从高分到低分跳过硬性底线冲突，取前 max_n 个可配。

    scored_pairs: [(other, score), ...]（建议已按分降序）
    Returns:
        (kept, dealbreaker_skipped)
        kept: [(other, score), ...]
    """
    kept = []
    skipped = 0
    limit = None if max_n is None else max(1, int(max_n))
    for other, score in scored_pairs:
        if _dealbreaker_conflict(user, other):
            skipped += 1
            continue
        kept.append((other, score))
        if limit is not None and len(kept) >= limit:
            break
    return kept, skipped


def real_time_match(user, candidates, top_n=5, min_score=0.15):
    """
    实时匹配：余弦相似度 Top-N。

    user/candidates 必须有 .feature_vector 属性（list of float）
    不在此过滤硬性底线：由调用方按序跳过，避免 Top-1 冲突就放弃更低分可配人选。

    Returns:
        [(candidate_user, score), ...] 按分数降序
    """
    if not user.feature_vector:
        return []

    uv = user.feature_vector
    scored = []
    for c in candidates:
        if c.id == user.id:
            continue
        if not c.feature_vector:
            continue
        if not orientation_compatible(user, c):
            continue
        sim = pair_score(user, c)
        if sim >= min_score:
            scored.append((c, round(sim, 4)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


# ============================================================
# 匈牙利算法 (Kuhn-Munkres / Hungarian Algorithm)
# 用于二分图最大权完美匹配
# ============================================================

def hungarian_match(group_a, group_b, score_matrix):
    """
    匈牙利算法：为 group_a 中每个人分配 group_b 中唯一的匹配。

    Args:
        group_a: list of User objects (e.g. 女性)
        group_b: list of User objects (e.g. 男性)
        score_matrix: 2D list, score_matrix[i][j] = 兼容度分数 [0, 1]
                      如果 group_a[i] 和 group_b[j] 不应该匹配（如一票否决），
                      设为 -1 或 0

    Returns:
        list of (user_a, user_b, score) tuples, 每人最多出现一次
    """
    n = len(group_a)
    m = len(group_b)

    if n == 0 or m == 0:
        return []

    # 标准化为方阵（填充小值）
    size = max(n, m)
    cost = [[0.0] * size for _ in range(size)]

    for i in range(size):
        for j in range(size):
            if i < n and j < m:
                # 转换为最小化问题（匈牙利算法求最小代价）
                # 兼容度越高 → 代价越小
                cost[i][j] = 1.0 - score_matrix[i][j]
            else:
                cost[i][j] = 1.0  # 虚拟节点，最大代价

    # 匈牙利算法实现 (O(n³))
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)

    for i in range(1, size + 1):
        p[0] = i
        j0 = 0
        minv = [float('inf')] * (size + 1)
        used = [False] * (size + 1)

        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float('inf')
            j1 = 0

            for j in range(1, size + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j

            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta

            j0 = j1
            if p[j0] == 0:
                break

        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    # 提取结果
    matches = []
    matched_b = set()
    for j in range(1, size + 1):
        if p[j] != 0:
            i = p[j] - 1
            j_idx = j - 1
            if i < n and j_idx < m:
                score = score_matrix[i][j_idx]
                matches.append((group_a[i], group_b[j_idx], round(score, 4)))
                matched_b.add(j_idx)

    # 按分数降序排列
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches


def batch_match_school(users, filter_same_gender=True):
    """
    对学校内用户做全局匹配。

    - 默认按择偶取向双向过滤后贪心配对（支持同性/双性取向）
    - filter_same_gender=True 且全部为「异性取向」时，仍可用匈牙利二部图

    Returns:
        list of (user1, user2, score)
    """
    pool = [u for u in users if u.feature_vector and u.gender]

    # 经典异性池：双方都明确只要异性 → 匈牙利
    hetero = [
        u for u in pool
        if (u.gender == "female" and u.effective_looking_for() == "male")
        or (u.gender == "male" and u.effective_looking_for() == "female")
    ]
    has_non_hetero = any(u.effective_looking_for() in ("both", u.gender) for u in pool)

    if filter_same_gender and hetero and not has_non_hetero:
        group_a = [u for u in hetero if u.gender == "female"]
        group_b = [u for u in hetero if u.gender == "male"]
        if group_a and group_b:
            n, m = len(group_a), len(group_b)
            score_matrix = [[0.0] * m for _ in range(n)]
            for i in range(n):
                for j in range(m):
                    if not orientation_compatible(group_a[i], group_b[j]):
                        continue
                    if _dealbreaker_conflict(group_a[i], group_b[j]):
                        continue  # 一票否决：保持 0，不当作可配边
                    score_matrix[i][j] = pair_score(group_a[i], group_b[j])
            return hungarian_match(group_a, group_b, score_matrix)

    # 含同性/不限取向：贪心最大权匹配
    return greedy_match_all(pool, min_score=0.0, require_orientation=True)


def greedy_match_all(users, min_score=0.15, require_orientation=True):
    """
    贪心匹配。

    对所有用户两两计算相似度，按分数从高到低贪心配对。
    每人只能匹配一次。require_orientation 时要求双向择偶兼容。
    """
    pairs = []
    for u1, u2 in combinations(users, 2):
        if not u1.feature_vector or not u2.feature_vector:
            continue
        if require_orientation and not orientation_compatible(u1, u2):
            continue
        if _dealbreaker_conflict(u1, u2):
            continue
        sim = pair_score(u1, u2)
        if sim >= min_score:
            pairs.append((u1, u2, sim))

    pairs.sort(key=lambda x: x[2], reverse=True)

    matched_ids = set()
    results = []
    for u1, u2, score in pairs:
        if u1.id in matched_ids or u2.id in matched_ids:
            continue
        matched_ids.add(u1.id)
        matched_ids.add(u2.id)
        results.append((u1, u2, round(score, 4)))

    return results
