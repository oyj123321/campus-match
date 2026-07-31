#!/usr/bin/env python3
"""
CampusMatch 数据速查（只读）

用法（项目根目录）：
  python scripts/inspect_db.py
  python scripts/inspect_db.py --db /opt/campus-match/instance/campus_match.db
  python scripts/inspect_db.py users
  python scripts/inspect_db.py incomplete
  python scripts/inspect_db.py pool
  python scripts/inspect_db.py matches
  python scripts/inspect_db.py user --id 1
  python scripts/inspect_db.py user --email mc64796@um.edu.mo
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "instance" / "campus_match.db"


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        print(f"数据库不存在: {db_path}", file=sys.stderr)
        sys.exit(1)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def cols(con: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}


def cmd_summary(con: sqlite3.Connection) -> None:
    uc = cols(con, "users")
    n_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    n_verified = con.execute(
        "SELECT COUNT(*) FROM users WHERE email_verified = 1"
    ).fetchone()[0]
    n_answers = con.execute(
        "SELECT COUNT(*) FROM users WHERE answers_json IS NOT NULL AND answers_json != '' AND answers_json != '{}'"
    ).fetchone()[0]
    n_matches = con.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    n_active = con.execute(
        "SELECT COUNT(*) FROM matches WHERE active = 1"
    ).fetchone()[0]

    print("=== 概览 ===")
    print(f"users 总计: {n_users}")
    print(f"  已验证邮箱: {n_verified}")
    print(f"  有问卷答案: {n_answers}")
    print(f"matches 总计: {n_matches}（active={n_active}）")
    if "open_to_match" in uc:
        n_open = con.execute(
            "SELECT COUNT(*) FROM users WHERE open_to_match IS NULL OR open_to_match = 1"
        ).fetchone()[0]
        print(f"  open_to_match 开/空: {n_open}")
    print()


def cmd_users(con: sqlite3.Connection, limit: int) -> None:
    uc = cols(con, "users")
    extra = []
    if "open_to_match" in uc:
        extra.append("open_to_match")
    if "opt_in_week" in uc:
        extra.append("opt_in_week")
    if "mbti_json" in uc:
        extra.append("mbti_json")
    sel = (
        "id, email, name, school, gender, looking_for, wechat_id, email_verified, created_at"
        + (", " + ", ".join(extra) if extra else "")
    )
    rows = con.execute(
        f"SELECT {sel} FROM users ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    print(f"=== 用户（最近 {len(rows)} 条）===")
    for r in rows:
        mbti = ""
        if "mbti_json" in r.keys() and r["mbti_json"]:
            try:
                mbti = json.loads(r["mbti_json"]).get("type", "")
            except (TypeError, ValueError, json.JSONDecodeError):
                mbti = "?"
        print(
            f"#{r['id']:>3} | {'✓' if r['email_verified'] else '·'} | {r['email']}"
            f" | {r['name'] or '（无名）'} | {r['school']}"
            f" | {r['gender'] or '-'}→{r['looking_for'] or '-'}"
            f" | wx={'(有)' if r['wechat_id'] else '(无)'}"
            f"{(' | ' + mbti) if mbti else ''}"
        )
    print()


def cmd_incomplete(con: sqlite3.Connection) -> None:
    rows = con.execute(
        """
        SELECT id, email, name, school, email_verified, gender, looking_for, wechat_id,
               CASE WHEN answers_json IS NULL OR answers_json = '' OR answers_json = '{}'
                    THEN 0 ELSE 1 END AS has_answers,
               created_at
        FROM users
        WHERE email_verified = 0
           OR name IS NULL OR name = ''
           OR gender IS NULL OR gender = ''
           OR looking_for IS NULL OR looking_for = ''
           OR wechat_id IS NULL OR wechat_id = ''
           OR answers_json IS NULL OR answers_json = '' OR answers_json = '{}'
        ORDER BY id
        """
    ).fetchall()
    print(f"=== 未完成注册/问卷（{len(rows)}）===")
    for r in rows:
        flags = []
        if not r["email_verified"]:
            flags.append("未验证")
        if not r["name"]:
            flags.append("无名")
        if not r["gender"]:
            flags.append("无性别")
        if not r["looking_for"]:
            flags.append("无取向")
        if not r["wechat_id"]:
            flags.append("无联系方式")
        if not r["has_answers"]:
            flags.append("无问卷")
        print(f"#{r['id']} {r['email']} | {', '.join(flags)} | {r['created_at']}")
    print()


def cmd_pool(con: sqlite3.Connection) -> None:
    """近似 in_match_pool：已验证 + 有向量 + 性别取向微信 + open_to_match。"""
    uc = cols(con, "users")
    open_clause = "1=1"
    if "open_to_match" in uc:
        open_clause = "(open_to_match IS NULL OR open_to_match = 1)"
    rows = con.execute(
        f"""
        SELECT id, email, name, school, gender, looking_for, opt_in_week
        FROM users
        WHERE email_verified = 1
          AND feature_vector_json IS NOT NULL AND feature_vector_json != ''
          AND gender IN ('male', 'female')
          AND looking_for IN ('male', 'female', 'both')
          AND wechat_id IS NOT NULL AND wechat_id != ''
          AND {open_clause}
        ORDER BY school, id
        """
    ).fetchall()
    print(f"=== 近似匹配池（{len(rows)}）===")
    by_school: dict[str, int] = {}
    for r in rows:
        by_school[r["school"]] = by_school.get(r["school"], 0) + 1
        opt = r["opt_in_week"] if "opt_in_week" in r.keys() else None
        print(
            f"#{r['id']} {r['name'] or '?'} | {r['school']} | {r['gender']}→{r['looking_for']}"
            f" | opt_in={opt or '-'} | {r['email']}"
        )
    print("--- 按校 ---")
    for s, n in sorted(by_school.items(), key=lambda x: -x[1]):
        print(f"  {s}: {n}")
    print()


def cmd_matches(con: sqlite3.Connection, limit: int) -> None:
    rows = con.execute(
        """
        SELECT m.id, m.user1_id, m.user2_id, m.score, m.active, m.mode, m.created_at,
               u1.name AS n1, u1.email AS e1, u1.school AS s1,
               u2.name AS n2, u2.email AS e2, u2.school AS s2
        FROM matches m
        LEFT JOIN users u1 ON u1.id = m.user1_id
        LEFT JOIN users u2 ON u2.id = m.user2_id
        ORDER BY m.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    print(f"=== 配对（最近 {len(rows)}）===")
    for r in rows:
        flag = "active" if r["active"] else "off"
        print(
            f"#{r['id']} [{flag}] {r['score']:.3f} | "
            f"{r['n1'] or '?'}({r['s1']}) ↔ {r['n2'] or '?'}({r['s2']}) | {r['created_at']}"
        )
        print(f"         {r['e1']} ↔ {r['e2']}")
    print()


def cmd_user(con: sqlite3.Connection, user_id: int | None, email: str | None) -> None:
    if user_id is not None:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    elif email:
        row = con.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    else:
        print("请指定 --id 或 --email", file=sys.stderr)
        sys.exit(2)
    if not row:
        print("未找到用户")
        return
    print("=== 用户详情 ===")
    skip = {"answers_json", "feature_vector_json", "mbti_json", "important_qids_json", "cross_schools_json"}
    for k in row.keys():
        if k in skip:
            continue
        print(f"  {k}: {row[k]}")
    ans = row["answers_json"] if "answers_json" in row.keys() else None
    if ans:
        try:
            d = json.loads(ans)
            print(f"  answers: {len(d)} 题")
        except (TypeError, ValueError, json.JSONDecodeError):
            print("  answers: (无法解析)")
    else:
        print("  answers: (空)")
    if "mbti_json" in row.keys() and row["mbti_json"]:
        try:
            m = json.loads(row["mbti_json"])
            print(f"  mbti: {m.get('type')} · {m.get('label')}")
        except (TypeError, ValueError, json.JSONDecodeError):
            print("  mbti: (无法解析)")
    uid = row["id"]
    ms = con.execute(
        """
        SELECT id, user1_id, user2_id, score, active, created_at
        FROM matches WHERE user1_id = ? OR user2_id = ? ORDER BY id DESC
        """,
        (uid, uid),
    ).fetchall()
    print(f"  matches: {len(ms)}")
    for m in ms:
        print(f"    #{m['id']} score={m['score']} active={m['active']} {m['created_at']}")
    print()


def main() -> None:
    p = argparse.ArgumentParser(description="CampusMatch SQLite 只读速查")
    p.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"数据库路径（默认 {DEFAULT_DB}）",
    )
    p.add_argument("--limit", type=int, default=50, help="列表条数上限")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("summary", help="概览（默认）")
    sub.add_parser("users", help="用户列表")
    sub.add_parser("incomplete", help="未完成注册/问卷")
    sub.add_parser("pool", help="近似匹配池")
    sub.add_parser("matches", help="配对列表")
    u = sub.add_parser("user", help="单用户详情")
    u.add_argument("--id", type=int)
    u.add_argument("--email", type=str)

    args = p.parse_args()
    con = connect(args.db)
    cmd = args.cmd or "summary"

    if cmd == "summary":
        cmd_summary(con)
        cmd_users(con, min(args.limit, 20))
        cmd_incomplete(con)
    elif cmd == "users":
        cmd_users(con, args.limit)
    elif cmd == "incomplete":
        cmd_incomplete(con)
    elif cmd == "pool":
        cmd_pool(con)
    elif cmd == "matches":
        cmd_matches(con, args.limit)
    elif cmd == "user":
        cmd_user(con, args.id, args.email)
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
