"""邮件发送服务 — 验证码 + 匹配通知"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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

    return _send_smtp(to_email, subject, body, mail_config)


def send_match_result_email(to_email, matches, mail_config, insight=None):
    """发送匹配结果邮件"""
    site_url = mail_config.get("public_url", "#")

    if not matches:
        body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;max-width:480px;margin:0 auto;padding:24px;">
    <div style="text-align:center;padding:24px 0;">
        <h1 style="color:#2563eb;">CampusMatch</h1>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;text-align:center;">
        <p style="font-size:18px;">😔 本次暂无匹配</p>
        <p style="color:#64748b;">试试修改问卷答案，扩大兴趣范围？</p>
        <a href="{site_url}/questionnaire" style="display:inline-block;margin-top:12px;padding:10px 24px;background:#ec4899;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">修改问卷</a>
    </div>
</body>
</html>"""
    else:
        rows = ""
        for i, (m_user, score) in enumerate(matches, 1):
            rows += f"""
            <tr>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;text-align:center;">#{i}</td>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;">{m_user.name or '(匿名)'}</td>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;text-align:center;color:#2563eb;font-weight:700;">{score:.0%}</td>
                <td style="padding:10px 8px;border-bottom:1px solid #e2e8f0;color:#059669;font-weight:700;">{m_user.wechat_id or '未填'}</td>
            </tr>"""

        insight_html = ""
        if insight:
            if insight.get("summary"):
                insight_html += (
                    f"<div style='background:#eff6ff;border-radius:8px;padding:12px 16px;margin-top:16px;'>"
                    f"<strong style='color:#1d4ed8;'>相处说明书</strong>"
                    f"<p style='margin:8px 0 0;font-size:14px;line-height:1.6;'>{insight['summary']}</p></div>"
                )
            strengths = insight.get("strengths", [])[:5]
            differences = insight.get("differences", [])[:3]
            if strengths:
                items = "".join(f"<li style='margin:4px 0;'>{s}</li>" for s in strengths)
                insight_html += f"<div style='background:#f0fdf4;border-radius:8px;padding:12px 16px;margin-top:16px;'><strong style='color:#059669;'>共同点</strong><ul style='margin:8px 0 0;padding-left:18px;font-size:14px;'>{items}</ul></div>"
            if differences:
                items = "".join(f"<li style='margin:4px 0;'>{d}</li>" for d in differences)
                insight_html += f"<div style='background:#fffbeb;border-radius:8px;padding:12px 16px;margin-top:10px;'><strong style='color:#92400e;'>需要注意的差异</strong><ul style='margin:8px 0 0;padding-left:18px;font-size:14px;'>{items}</ul></div>"
            ice = insight.get("icebreakers", [])[:3]
            if ice:
                items = "".join(f"<li style='margin:4px 0;'>{x}</li>" for x in ice)
                insight_html += f"<div style='background:#fdf2f8;border-radius:8px;padding:12px 16px;margin-top:10px;'><strong style='color:#be185d;'>破冰话题（别让聊天死掉）</strong><ul style='margin:8px 0 0;padding-left:18px;font-size:14px;'>{items}</ul></div>"

        body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1e293b;">
    <div style="text-align:center;padding:24px 0;">
        <h1 style="color:#ec4899;margin:0;">匹配结果</h1>
        <p style="color:#64748b;font-size:14px;">算法为你找到以下有缘人</p>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="background:#f8fafc;">
                    <th style="padding:10px 8px;text-align:left;font-size:13px;color:#64748b;">#</th>
                    <th style="padding:10px 8px;text-align:left;font-size:13px;color:#64748b;">名字</th>
                    <th style="padding:10px 8px;text-align:left;font-size:13px;color:#64748b;">匹配度</th>
                    <th style="padding:10px 8px;text-align:left;font-size:13px;color:#64748b;">微信</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        {insight_html}
    </div>
    <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:24px;">
        匹配基于 CampusMatch 32 题深度问卷。<br>算法只能帮你找到可能合拍的人，剩下的靠你们自己 ✨
    </p>
</body>
</html>"""

    subject = "CampusMatch - 你的匹配结果"

    if not mail_config.get("enabled"):
        print(f"\n{'='*60}")
        print(f"[DEV] 匹配结果 → {to_email}")
        for i, (m_user, score) in enumerate(matches, 1):
            print(f"  #{i} {m_user.name} | wx:{m_user.wechat_id} | {score:.0%}")
        if insight and insight.get("strengths"):
            print(f"  共同点: {' | '.join(insight['strengths'][:3])}")
        print(f"{'='*60}\n")
        return True, "dev-printed"

    return _send_smtp(to_email, subject, body, mail_config)


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
