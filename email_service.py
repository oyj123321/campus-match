"""邮件发送服务 — 验证码 + 匹配通知（SMTP / Resend）"""

import json
import smtplib
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _dispatch_email(to_email, subject, html_body, mail_config):
    """按 MAIL_PROVIDER 选择 Resend API 或 SMTP。"""
    provider = (mail_config.get("provider") or "smtp").strip().lower()
    if provider == "resend":
        return _send_resend(to_email, subject, html_body, mail_config)
    return _send_smtp(to_email, subject, html_body, mail_config)


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
            f"本轮情况：{reason_line}</p>"
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
    for i, (m_user, score) in enumerate(matches, 1):
        extra = m_user.wechat_id or ""
        extra_cell = (
            f'<td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;color:#059669;font-weight:700;">{extra}</td>'
            if extra else
            '<td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;color:#94a3b8;">—</td>'
        )
        rows += f"""
            <tr>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;text-align:center;">#{i}</td>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;">{m_user.name or '(匿名)'}</td>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;color:#2563eb;font-weight:600;">{m_user.email}</td>
                {extra_cell}
            </tr>"""

    insight_html = ""
    if insight:
        strengths = insight.get("strengths", [])[:4]
        if strengths:
            items = "".join(f"<li style='margin:4px 0;'>{s}</li>" for s in strengths)
            insight_html += f"<div style='background:#f0fdf4;border-radius:8px;padding:12px 16px;margin-top:16px;'><strong style='color:#059669;'>你们的契合点</strong><ul style='margin:8px 0 0;padding-left:18px;font-size:14px;'>{items}</ul></div>"
        letter = None
        try:
            from questionnaire import get_open_letter
            if matches:
                letter = get_open_letter(matches[0][0].answers)
        except Exception:
            letter = None
        if letter:
            safe = (
                letter.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\n", "<br>")
            )
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
                    tip = x.get("tip") or ""
                    send = x.get("send") or ""
                    chunk = tip
                    if send:
                        chunk += f"<br><em style='color:#9d174d;'>可以发：</em>{send}"
                    items.append(f"<li style='margin:8px 0;'>{chunk}</li>")
                else:
                    items.append(f"<li style='margin:4px 0;'>{x}</li>")
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
        {insight_html}
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
            print(f"  #{i} {m_user.name} | email:{m_user.email} | extra:{m_user.wechat_id or '-'}")
        if insight and insight.get("strengths"):
            print(f"  共同点: {' | '.join(insight['strengths'][:3])}")
        print(f"{'='*60}\n")
        return True, "dev-printed"

    return _dispatch_email(to_email, subject, body, mail_config)


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
