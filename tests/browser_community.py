"""Local end-to-end checks using synthetic data and a disposable in-memory server."""
import os
import threading
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
        Entry(author_id=uid,school=user.school,category="campus",title="图书馆窗边的晚霞",body="今天在图书馆看到了很好看的晚霞。你最近遇到过什么小确幸？"),
        Entry(author_id=uid,school=user.school,category="friends",title="周末一起去海边散步吗？",body="想约几位同学周末一起散步，欢迎在评论里聊聊计划。"),
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
            expect(guest.get_by_role("link",name="登录收藏",exact=True)).to_be_visible()
            assert guest.locator('form[data-community-action]').count() == 0
            assert guest.locator("body").evaluate("el => el.scrollWidth <= innerWidth")
            guest.close()
            cookie=app.session_interface.get_signing_serializer(app).dumps({"user_id":uid})
            context.add_cookies([{"name":"session","value":cookie,"url":base}])
            page=context.new_page()
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(base+"/community")
            assert page.get_by_role("heading",name="校园广场",exact=True).is_visible()
            assert page.locator("body").evaluate("el => el.scrollWidth <= innerWidth")
            page.screenshot(path=str(output/f"community-{width}.png"),full_page=True)
            page.get_by_role("link",name="图书馆窗边的晚霞",exact=True).click()
            page.evaluate("window.communityNavigationMarker = 42")
            page.get_by_role("button",name="赞 · 0",exact=True).click()
            expect(page.get_by_role("button",name="取消赞 · 1",exact=True)).to_be_visible()
            page.get_by_role("button",name="取消赞 · 1",exact=True).click()
            expect(page.get_by_role("button",name="赞 · 0",exact=True)).to_be_visible()
            page.get_by_role("button",name="收藏",exact=True).click()
            expect(page.get_by_role("button",name="取消收藏",exact=True)).to_be_visible()
            assert page.evaluate("window.communityNavigationMarker") == 42
            page.get_by_role("link",name="我的收藏",exact=True).click()
            assert page.get_by_role("heading",name="图书馆窗边的晚霞").count()==1
            if width==1440:
                page.get_by_role("link",name="＋ 发一条动态",exact=True).click()
                page.locator('[name="category"]').select_option("confession")
                page.locator('[name="title"]').fill("一封演示表白信")
                page.locator('[name="body"]').fill("感谢那天借给我雨伞的同学，愿你每一天都开心。")
                page.locator('[name="anonymous"]').check()
                page.get_by_role("button",name="提交发布",exact=True).click()
                expect(page.get_by_text("正在等待管理员审核，其他同学暂不可见。")).to_be_visible()
                page.goto(base+"/admin/community")
                page.locator('#password').fill("browser-test-admin")
                page.get_by_role("button",name="登录",exact=True).click()
                page.goto(base+"/admin/community")
                page.locator('[name="reason"]').first.fill("演示审核通过")
                page.get_by_role("button",name="审核通过",exact=True).first.click()
                page.goto(base+"/community?view=mine")
                page.get_by_role("link",name="一封演示表白信",exact=True).click()
                page.locator('textarea[name="body"]').fill("谢谢，也祝你今天开心。")
                page.get_by_role("button",name="发表评论",exact=True).click()
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
