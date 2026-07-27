"""邮件发送服务"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_verification_email(to_email, token, mail_config):
    """发送验证码邮件"""
    subject = "CampusMatch - 验证你的学校邮箱"
    body = f"""
    <h2>CampusMatch 🎓</h2>
    <p>你的验证码是：</p>
    <h1 style="color:#2563eb;font-size:2em;">{token}</h1>
    <p>10 分钟内有效。如果不是你本人操作，请忽略。</p>
    """

    if not mail_config.get("enabled"):
        print(f"\n{'='*60}")
        print(f"[DEV] 验证邮件 → {to_email} | Token: {token}")
        print(f"{'='*60}\n")
        return True, "dev-printed"

    return _send_smtp(to_email, subject, body, mail_config)


def send_match_result_email(to_email, matches, mail_config, insight=None):
    """
    发送匹配结果邮件。

    Args:
        to_email: 收件人邮箱
        matches: [(matched_user, score), ...]
        mail_config: SMTP 配置
        insight: dict with 'strengths' and 'differences' (兼容性分析)
    """
    if not matches:
        body = """
        <h2>本次匹配结果</h2>
        <p>暂时没有匹配到与你有缘的同学 😔</p>
        <p>试试修改问卷答案，扩大兴趣范围？</p>
        """
    else:
        rows = ""
        for i, (m_user, score) in enumerate(matches, 1):
            rows += f"""
            <tr>
                <td style="padding:8px;border:1px solid #ddd;">#{i}</td>
                <td style="padding:8px;border:1px solid #ddd;">{m_user.name or '(匿名)'}</td>
                <td style="padding:8px;border:1px solid #ddd;color:#2563eb;font-weight:bold;">{score:.1%}</td>
                <td style="padding:8px;border:1px solid #ddd;color:#059669;font-weight:bold;">{m_user.wechat_id or '未填写'}</td>
            </tr>"""

        # 匹配理由
        insight_html = ""
        if insight:
            strengths = insight.get("strengths", [])[:5]
            differences = insight.get("differences", [])[:3]
            if strengths:
                items = "".join(f"<li>{s}</li>" for s in strengths)
                insight_html += f"<h3>💚 你们的共同点</h3><ul>{items}</ul>"
            if differences:
                items = "".join(f"<li>{d}</li>" for d in differences)
                insight_html += f"<h3>⚡ 需要注意的差异</h3><ul>{items}</ul>"

        body = f"""
        <h2>🎉 你的匹配结果</h2>
        <p>系统通过深度问卷分析，为你找到以下匹配：</p>
        <table style="border-collapse:collapse;width:100%;">
            <thead>
                <tr style="background:#f0f0f0;">
                    <th style="padding:8px;border:1px solid #ddd;">排名</th>
                    <th style="padding:8px;border:1px solid #ddd;">名字</th>
                    <th style="padding:8px;border:1px solid #ddd;">匹配度</th>
                    <th style="padding:8px;border:1px solid #ddd;">微信号</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        {insight_html}
        <p style="margin-top:16px;color:#999;font-size:13px;">
            匹配基于你在 CampusMatch 填写的 32 题深度问卷。<br>
            算法只能帮你找到可能合拍的人，剩下的靠你们自己 ✨
        </p>
        """

    subject = "CampusMatch - 你的匹配结果"

    if not mail_config.get("enabled"):
        print(f"\n{'='*60}")
        print(f"[DEV] 匹配结果 → {to_email}")
        for i, (m_user, score) in enumerate(matches, 1):
            print(f"  #{i} {m_user.name} | wx:{m_user.wechat_id} | {score:.1%}")
        if insight and insight.get("strengths"):
            print(f"  共同点: {', '.join(insight['strengths'][:3])}")
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
