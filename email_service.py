"""邮件发送服务 — 验证码 + 匹配通知（SMTP / Resend）"""

import json
import smtplib
import urllib.error
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _html_esc(s):
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _dispatch_email(to_email, subject, html_body, mail_config):
    """按 MAIL_PROVIDER 选择 Resend API 或 SMTP。"""
    try:
        provider = (mail_config.get("provider") or "smtp").strip().lower()
        if provider == "resend":
            return _send_resend(to_email, subject, html_body, mail_config)
        return _send_smtp(to_email, subject, html_body, mail_config)
    except Exception as e:
        print(f"[ERROR] 发信异常 → {to_email}: {e}")
        return False, str(e)


def send_verification_email(to_email, token, mail_config):
    """发送验证码邮件"""
    site_url = mail_config.get("public_url", "#")
    subject = "CampusMatch - 验证你的学校邮箱"

    body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1e293b;">
    <div style="text-align:center;padding:24px 0;">
        <h1 style="color:#2563eb;margin:0;">CampusMatch</h1>
        <p style="color:#64748b;font-size:14px;">校园恋爱匹配 · 深度问卷 · 每周二晚匹配</p>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
        <p style="font-size:16px;">你好！有人在 <a href="{site_url}" style="color:#2563eb;">CampusMatch</a> 用这个邮箱注册了账号。</p>
        <p style="font-size:16px;margin-top:16px;">你的验证码是：</p>
        <div style="text-align:center;margin:24px 0;">
            <span style="font-size:36px;font-weight:800;letter-spacing:8px;color:#2563eb;background:#eff6ff;padding:12px 24px;border-radius:8px;">{token}</span>
        </div>
        <p style="color:#64748b;font-size:13px;">验证码 10 分钟内有效。如果不是你本人操作，请忽略此邮件。</p>
    </div>
    <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:24px;">CampusMatch · 用算法连接校园里有缘的人</p>
</body>
</html>"""

    if not mail_config.get("enabled"):
        print(f"\n{'='*60}")
        print(f"[DEV] 验证码 → {to_email}")
        print(f"[DEV] Token: {token}")
        print(f"{'='*60}\n")
        return True, "dev-printed"

    return _dispatch_email(to_email, subject, body, mail_config)


def send_match_result_email(to_email, matches, mail_config, insight=None, reason=None):
    """发送匹配结果邮件。matches 为空时发「暂未配对」说明。
    reason: 可选，本轮未配上的简要原因（给人看的人话）。
    """
    site_url = mail_config.get("public_url", "#")

    if not matches:
        reason_line = (reason or "").strip()
        reason_html = (
            f"<p style='color:#475569;font-size:14px;line-height:1.7;margin:16px 0 0;'>"
            f"本轮情况：{_html_esc(reason_line)}</p>"
            if reason_line else ""
        )
        subject = "CampusMatch - 本次暂未配对"
        body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1e293b;">
    <div style="text-align:center;padding:24px 0;">
        <h1 style="color:#ec4899;margin:0;">本次暂未配对</h1>
        <p style="color:#64748b;font-size:14px;margin:8px 0 0;">结果已出——这一轮没有合适的人</p>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
        <p style="font-size:16px;line-height:1.7;margin:0;">
            你好，本轮匹配已经跑完了。系统按你的取向与问卷看过池子里的同学，
            <strong>这一次没有给你配对</strong>。
        </p>
        {reason_html}
        <p style="font-size:14px;line-height:1.7;color:#64748b;margin:16px 0 0;">
            常见原因：池子里人还不多、取向或硬性底线对不上、合适的人本周已经配过
            （每人每周最多参与一次）。这不是否定你，而是宁缺毋滥。
        </p>
        <p style="font-size:14px;line-height:1.7;margin:16px 0 0;">
            你可以下周再参加揭晓，或在网站上完善问卷；人多起来后机会也会更多。
            详情以网站「匹配结果」页为准。
        </p>
        <div style="text-align:center;margin-top:20px;">
            <a href="{site_url}/matches" style="display:inline-block;padding:10px 24px;background:#ec4899;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">打开匹配页</a>
        </div>
    </div>
    <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:24px;">CampusMatch · 用算法连接校园里有缘的人</p>
</body>
</html>"""
        if not mail_config.get("enabled"):
            print(f"\n{'='*60}")
            print(f"[DEV] 暂未配对通知 → {to_email}")
            if reason_line:
                print(f"[DEV] reason: {reason_line}")
            print(f"{'='*60}\n")
            return True, "dev-printed"
        return _dispatch_email(to_email, subject, body, mail_config)

    rows = ""
    any_privacy = False
    for i, (m_user, score) in enumerate(matches, 1):
        extra = _html_esc(m_user.wechat_id or "")
        extra_cell = (
            f'<td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;color:#059669;font-weight:700;">{extra}</td>'
            if extra else
            '<td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;color:#94a3b8;">—</td>'
        )
        is_privacy = False
        fn = getattr(m_user, "is_express", None)
        if callable(fn):
            is_privacy = bool(fn())
        else:
            is_privacy = (getattr(m_user, "profile_mode", None) or "full") in ("express", "privacy")
        if is_privacy:
            any_privacy = True
        badge = (
            ' <span style="display:inline-block;padding:2px 8px;border-radius:99px;'
            'background:#fef3c7;color:#92400e;font-size:12px;font-weight:700;">隐私用户</span>'
            if is_privacy else ""
        )
        display_name = _html_esc(m_user.name or "(匿名)")
        rows += f"""
            <tr>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;text-align:center;">#{i}</td>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;">{display_name}{badge}</td>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;color:#2563eb;font-weight:600;">{_html_esc(m_user.email)}</td>
                {extra_cell}
            </tr>"""
        bio = (getattr(m_user, "bio", None) or "").strip()
        if is_privacy and bio:
            safe_bio = _html_esc(bio).replace("\n", "<br>")
            rows += f"""
            <tr>
                <td colspan="4" style="padding:4px 8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#475569;line-height:1.65;">
                    <strong style="color:#92400e;">自我介绍：</strong>{safe_bio}
                </td>
            </tr>"""

    privacy_html = ""
    if any_privacy:
        privacy_html = (
            "<div style='background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:12px 16px;margin-top:16px;'>"
            "<strong style='color:#92400e;'>对方是隐私用户</strong>"
            "<p style='margin:8px 0 0;font-size:14px;line-height:1.65;color:#78350f;'>"
            "TA 选择了隐私模式，没有填完整问卷，资料更少。请尊重边界，用学校邮箱慢慢聊。"
            "</p></div>"
        )

    insight_html = ""
    if insight:
        strengths = insight.get("strengths", [])[:4]
        if strengths:
            items = "".join(f"<li style='margin:4px 0;'>{_html_esc(s)}</li>" for s in strengths)
            insight_html += f"<div style='background:#f0fdf4;border-radius:8px;padding:12px 16px;margin-top:16px;'><strong style='color:#059669;'>你们的契合点</strong><ul style='margin:8px 0 0;padding-left:18px;font-size:14px;'>{items}</ul></div>"
        letter = None
        try:
            from questionnaire import get_open_letter
            if matches:
                letter = get_open_letter(matches[0][0].answers)
        except Exception:
            letter = None
        if letter:
            safe = _html_esc(letter).replace("\n", "<br>")
            insight_html += (
                f"<div style='background:#f0fdfa;border-radius:8px;padding:12px 16px;margin-top:10px;'>"
                f"<strong style='color:#0f766e;'>TA 留给你的话</strong>"
                f"<p style='margin:8px 0 0;font-size:14px;line-height:1.65;'>{safe}</p></div>"
            )
        ice = insight.get("icebreakers", [])[:3]
        if ice:
            items = []
            for x in ice:
                if isinstance(x, dict):
                    tip = _html_esc(x.get("tip") or "")
                    send = _html_esc(x.get("send") or "")
                    chunk = tip
                    if send:
                        chunk += f"<br><em style='color:#9d174d;'>可以发：</em>{send}"
                    items.append(f"<li style='margin:8px 0;'>{chunk}</li>")
                else:
                    items.append(f"<li style='margin:4px 0;'>{_html_esc(x)}</li>")
            insight_html += (
                f"<div style='background:#fdf2f8;border-radius:8px;padding:12px 16px;margin-top:10px;'>"
                f"<strong style='color:#be185d;'>破冰话题</strong>"
                f"<ul style='margin:8px 0 0;padding-left:18px;font-size:14px;'>{''.join(items)}</ul></div>"
            )

    body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1e293b;">
    <div style="text-align:center;padding:24px 0;">
        <h1 style="color:#ec4899;margin:0;">匹配结果</h1>
        <p style="color:#64748b;font-size:14px;">算法为你找到以下有缘人——分数不重要，聊起来才重要</p>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="background:#f8fafc;">
                    <th style="padding:10px 8px;text-align:left;font-size:13px;color:#64748b;">#</th>
                    <th style="padding:10px 8px;text-align:left;font-size:13px;color:#64748b;">名字</th>
                    <th style="padding:10px 8px;text-align:left;font-size:13px;color:#64748b;">学校邮箱</th>
                    <th style="padding:10px 8px;text-align:left;font-size:13px;color:#64748b;">附加联系</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        {privacy_html}
        {insight_html}
        <p style="font-size:13px;line-height:1.7;color:#64748b;margin:18px 0 0;">
            建议尽快打个招呼（学校邮箱或附加联系方式均可）。友善、真诚比完美开场白更重要。
        </p>
        <p style="font-size:12px;line-height:1.7;color:#94a3b8;margin:10px 0 0;">
            若暂时不想继续被匹配，可在网站「匹配中心」关闭「参与匹配」——资料会保留，历史结果仍可查看。
        </p>
    </div>
    <p style="text-align:center;margin-top:16px;">
        <a href="{site_url}/matches" style="display:inline-block;padding:10px 24px;background:#ec4899;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">打开匹配页查看详情</a>
    </p>
    <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:24px;">
        匹配基于 CampusMatch 深度问卷。<br>算法只能帮你找到可能合拍的人，剩下的靠你们自己 ✨
    </p>
</body>
</html>"""

    subject = "CampusMatch - 你的匹配结果"

    if not mail_config.get("enabled"):
        print(f"\n{'='*60}")
        print(f"[DEV] 匹配结果 → {to_email}")
        for i, (m_user, score) in enumerate(matches, 1):
            mode = "隐私用户" if getattr(m_user, "is_express", lambda: False)() else "问卷用户"
            print(f"  #{i} {m_user.name} | {mode} | email:{m_user.email} | extra:{m_user.wechat_id or '-'}")
        if insight and insight.get("strengths"):
            print(f"  共同点: {' | '.join(insight['strengths'][:3])}")
        print(f"{'='*60}\n")
        return True, "dev-printed"

    return _dispatch_email(to_email, subject, body, mail_config)


def send_icebreaker_followup_email(to_email, partner_name, mail_config):
    """配对约 3 天后催破冰（打招呼）。"""
    site_url = mail_config.get("public_url", "#")
    name = (partner_name or "对方").strip() or "对方"
    safe_name = (
        name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    subject = "CampusMatch - 和 TA 打个招呼了吗？"
    body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1e293b;">
    <div style="text-align:center;padding:20px 0;">
        <h1 style="color:#ec4899;margin:0;font-size:22px;">还记得这次的配对吗？</h1>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
        <p style="font-size:16px;line-height:1.7;margin:0;">
            你好，你和 <strong>{safe_name}</strong> 已经配对几天了。
            如果还没联系，不妨用学校邮箱或附加联系方式<strong>先打个招呼</strong>——一句你好就很好。
        </p>
        <p style="font-size:14px;line-height:1.7;color:#64748b;margin:16px 0 0;">
            请友善、真诚；对方也是同校同学。聊不来也没关系，礼貌收尾即可。
        </p>
        <div style="text-align:center;margin-top:20px;">
            <a href="{site_url}/matches" style="display:inline-block;padding:10px 24px;background:#ec4899;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">打开匹配页</a>
        </div>
        <p style="font-size:12px;line-height:1.7;color:#94a3b8;margin:16px 0 0;">
            若暂时不想继续匹配，可在匹配中心关闭「参与匹配」。
        </p>
    </div>
</body>
</html>"""
    if not mail_config.get("enabled"):
        print(f"[DEV] 破冰随访 → {to_email} · partner={name}")
        return True, "dev-printed"
    return _dispatch_email(to_email, subject, body, mail_config)


def send_incomplete_nudge_email(to_email, mail_config, name=None):
    """催未完成问卷的用户回来续填。"""
    site_url = (mail_config.get("public_url") or "#").rstrip("/")
    continue_url = f"{site_url}/questionnaire"
    display = (name or "").strip() or "同学"
    safe_name = (
        display.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    subject = "CampusMatch - 问卷还没填完，回来继续？"
    body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1e293b;">
    <div style="text-align:center;padding:20px 0;">
        <h1 style="color:#2563eb;margin:0;font-size:22px;">问卷还差几步</h1>
        <p style="color:#64748b;font-size:14px;margin:8px 0 0;">填完才能进本周匹配池</p>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
        <p style="font-size:16px;line-height:1.7;margin:0;">
            你好，{safe_name}！你已验证学校邮箱，但资料问卷还没答完。
            未完成问卷时<strong>无法参与每周一对一匹配</strong>。
        </p>
        <p style="font-size:14px;line-height:1.7;color:#64748b;margin:16px 0 0;">
            点下面链接登录后继续填写（进度会保留）。填完也不保证一定配上——池子小、取向不合或硬性底线冲突时可能暂无对象。
        </p>
        <div style="text-align:center;margin-top:20px;">
            <a href="{continue_url}" style="display:inline-block;padding:10px 24px;background:#2563eb;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">继续填写问卷</a>
        </div>
        <p style="font-size:12px;line-height:1.7;color:#94a3b8;margin:16px 0 0;">
            若打不开链接，请打开 {site_url} 用学校邮箱登录后进入「问卷」。
        </p>
    </div>
    <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:24px;">CampusMatch · 用算法连接校园里有缘的人</p>
</body>
</html>"""
    if not mail_config.get("enabled"):
        print(f"[DEV] 未完成问卷催填 → {to_email} · link={continue_url}")
        return True, "dev-printed"
    return _dispatch_email(to_email, subject, body, mail_config)


def send_incomplete_nudges(mail_config, cooldown_days=None, limit=200, dry_run=True):
    """给 verified 且问卷未完成的用户发催填信。

    返回 dict: candidates / sent / skipped_cooldown / failed / disabled / dry_run
    """
    from datetime import timedelta
    from models import db, User
    from config import (
        MAIL_INCOMPLETE_NUDGE_ENABLED,
        INCOMPLETE_NUDGE_COOLDOWN_DAYS,
    )

    if cooldown_days is None:
        cooldown_days = INCOMPLETE_NUDGE_COOLDOWN_DAYS
    cooldown_days = max(1, int(cooldown_days))
    limit = max(1, int(limit))

    result = {
        "dry_run": bool(dry_run),
        "enabled": MAIL_INCOMPLETE_NUDGE_ENABLED,
        "cooldown_days": cooldown_days,
        "candidates": 0,
        "sent": 0,
        "skipped_cooldown": 0,
        "failed": 0,
        "emails": [],
    }
    if not MAIL_INCOMPLETE_NUDGE_ENABLED:
        result["disabled"] = True
        return result

    cutoff = datetime.utcnow() - timedelta(days=cooldown_days)
    verified = (
        User.query.filter(User.email_verified.is_(True))
        .order_by(User.id.asc())
        .all()
    )
    targets = []
    for u in verified:
        if u.ready_to_match():
            continue
        if u.incomplete_nudge_at and u.incomplete_nudge_at > cutoff:
            result["skipped_cooldown"] += 1
            continue
        targets.append(u)
        if len(targets) >= limit:
            break

    result["candidates"] = len(targets)
    for u in targets:
        result["emails"].append(u.email)
        if dry_run:
            continue
        ok, _info = send_incomplete_nudge_email(u.email, mail_config, name=u.name)
        if ok:
            u.incomplete_nudge_at = datetime.utcnow()
            result["sent"] += 1
        else:
            result["failed"] += 1
    if not dry_run and result["sent"]:
        db.session.commit()
    return result


def send_due_icebreaker_followups(mail_config):
    """扫描到期配对，各发一封破冰随访；返回处理对数。"""
    from datetime import timedelta
    from models import db, Match, User
    from match_pool import is_blocked_pair
    from config import ICEBREAKER_FOLLOWUP_DAYS, ICEBREAKER_FOLLOWUP_ENABLED

    if not ICEBREAKER_FOLLOWUP_ENABLED:
        return 0

    cutoff = datetime.utcnow() - timedelta(days=max(1, ICEBREAKER_FOLLOWUP_DAYS))
    rows = (
        Match.query.filter(
            Match.icebreaker_followup_sent.is_(False),
            Match.notified.is_(True),
            Match.created_at <= cutoff,
        )
        .order_by(Match.created_at.asc())
        .limit(80)
        .all()
    )
    handled = 0
    for m in rows:
        a = User.query.get(m.user1_id)
        b = User.query.get(m.user2_id)
        if not a or not b:
            m.icebreaker_followup_sent = True
            handled += 1
            continue
        if is_blocked_pair(a.id, b.id):
            m.icebreaker_followup_sent = True
            handled += 1
            continue
        send_icebreaker_followup_email(a.email, b.name or "对方", mail_config)
        send_icebreaker_followup_email(b.email, a.name or "对方", mail_config)
        m.icebreaker_followup_sent = True
        handled += 1
    if handled:
        db.session.commit()
    return handled


def _send_resend(to_email, subject, html_body, mail_config):
    api_key = (mail_config.get("resend_api_key") or "").strip()
    if not api_key:
        print(f"[ERROR] Resend 未配置 RESEND_API_KEY → {to_email}")
        return False, "missing RESEND_API_KEY"

    payload = {
        "from": mail_config["mail_from"],
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Resend 在 Cloudflare 后：无 User-Agent 会 403 / error code 1010
            "User-Agent": "CampusMatch/1.0 (+https://campusmatch.com.cn)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, body or "sent"
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] Resend 发送失败 → {to_email}: HTTP {e.code} {err}")
        return False, err or str(e)
    except Exception as e:
        print(f"[ERROR] Resend 发送失败 → {to_email}: {e}")
        return False, str(e)


def _send_smtp(to_email, subject, html_body, mail_config):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_config["mail_from"]
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(mail_config["server"], mail_config["port"], timeout=10)
        server.starttls()
        server.login(mail_config["username"], mail_config["password"])
        server.sendmail(mail_config["mail_from"], [to_email], msg.as_string())
        server.quit()
        return True, "sent"
    except Exception as e:
        print(f"[ERROR] 邮件发送失败 → {to_email}: {e}")
        return False, str(e)
