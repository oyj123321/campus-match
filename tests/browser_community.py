"""Local end-to-end checks using synthetic data and a disposable in-memory server."""
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, session
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server, WSGIRequestHandler

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import admin_dashboard
from community import bp
from models import db, User, CommunityEntry as Entry, CommunityReaction


app = Flask(__name__, template_folder=str(ROOT/"templates"), static_folder=str(ROOT/"static"))
app.config.update(SECRET_KEY="disposable-community-browser-test", SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
db.init_app(app)
app.register_blueprint(admin_dashboard.bp)
app.register_blueprint(bp)
admin_dashboard.ADMIN_SECRET = "browser-test-admin"


@app.context_processor
def globals_for_base():
    return dict(current_user=db.session.get(User,session.get("user_id")) if session.get("user_id") else None,
                public_url="",contact_email="demo@example.test",site_announcement="演示数据 · 浏览器测试",
                questionnaire_incomplete=False)


with app.app_context():
    db.create_all()
    user=User(email="demo@example.test",school="澳门大学",name="演示同学",email_verified=True)
    db.session.add(user)
    db.session.flush()
    uid=user.id
    db.session.add_all([
        Entry(author_id=uid,school=user.school,category="study",title="图书馆窗边的晚霞",body="今晚在图书馆写高数，还差一个人。",
             place="图书馆",capacity=4,fee="free",starts_at=datetime.utcnow()+timedelta(days=1)),
        Entry(author_id=uid,school=user.school,category="meal",title="周末一起去海边散步吗？",body="想约几位同学周末一起散步。",
             place="校园门口",capacity=4,fee="aa",starts_at=datetime.utcnow()+timedelta(days=2)),
    ])
    db.session.commit()

class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


server=make_server("127.0.0.1",0,app,threaded=True,request_handler=QuietHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}"
output=ROOT/"instance"
output.mkdir(exist_ok=True)

try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel=os.environ.get("ADMIN_BROWSER_CHANNEL") or None)
        for width,height in [(1440,1000),(390,844)]:
            with app.app_context():
                CommunityReaction.query.delete()
                db.session.commit()
            context=browser.new_context(viewport={"width":width,"height":height})
            guest=context.new_page()
            guest.goto(base+"/community")
            expect(guest.get_by_role("link",name="注册 / 登录参与",exact=True)).to_be_visible()
            guest.get_by_role("link",name="图书馆窗边的晚霞",exact=True).click()
            expect(guest.get_by_role("link",name="登录后收藏",exact=True)).to_be_visible()
            assert guest.locator('form[data-community-action]').count() == 0
            assert guest.locator("body").evaluate("el => el.scrollWidth <= innerWidth")
            guest.close()
            cookie=app.session_interface.get_signing_serializer(app).dumps({"user_id":uid})
            context.add_cookies([{"name":"session","value":cookie,"url":base}])
            page=context.new_page()
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(base+"/community")
            assert page.get_by_role("heading",name="找搭子",exact=True).is_visible()
            assert page.locator("body").evaluate("el => el.scrollWidth <= innerWidth")
            page.screenshot(path=str(output/f"community-{width}.png"),full_page=True)
            page.get_by_role("link",name="图书馆窗边的晚霞",exact=True).click()
            page.evaluate("window.communityNavigationMarker = 42")
            page.get_by_role("button",name="收藏",exact=True).click()
            expect(page.get_by_role("button",name="取消收藏",exact=True)).to_be_visible()
            assert page.evaluate("window.communityNavigationMarker") == 42
            page.get_by_role("link",name="收藏",exact=True).click()
            assert page.get_by_role("heading",name="图书馆窗边的晚霞").count()==1
            if width==1440:
                page.get_by_role("link",name="＋ 发起一场局",exact=True).click()
                page.locator('[name="category"]').select_option("study")
                page.locator('[name="title"]').fill("周六图书馆高数")
                page.locator('[name="place"]').fill("图书馆")
                page.locator('[name="capacity"]').fill("3")
                page.locator('[name="starts_at"]').fill("2026-12-01T19:00")
                page.locator('[name="body"]').fill("一起写题，不闲聊。")
                page.get_by_role("button",name="发布这场局",exact=True).click()
                expect(page.get_by_role("heading",name="周六图书馆高数",exact=True)).to_be_visible()
                page.locator('textarea[name="body"]').fill("谢谢，也祝你今天开心。")
                page.get_by_role("button",name="发表留言",exact=True).click()
                expect(page.get_by_text("谢谢，也祝你今天开心。",exact=True)).to_be_visible()
                page.screenshot(path=str(output/"community-detail.png"),full_page=True)
            page.goto(base+"/admin/login")
            if page.locator('#password').count():
                page.locator('#password').fill("browser-test-admin")
                page.locator('button[type="submit"]').click()
            page.goto(base+"/admin/community?state=published")
            assert page.get_by_role("heading",name="社区管理",exact=True).is_visible()
            assert page.locator("body").evaluate("el => el.scrollWidth <= innerWidth")
            page.screenshot(path=str(output/f"community-admin-{width}.png"),full_page=True)
            assert not errors,errors
            context.close()
        browser.close()
    print("Community desktop/mobile and publish-review-comment flows passed.")
finally:
    server.shutdown()
