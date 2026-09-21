import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from flask import Flask

import admin_dashboard
from community import bp, purge_community
from models import (db, User, CommunityEntry as Entry, CommunityReaction as Reaction,
                    CommunityReport as Report, CommunityBan as Ban,
                    CommunityLimit as Limit, CommunityAudit as Audit)


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1]/"templates"))
        self.app.config.update(TESTING=True, SECRET_KEY="community-tests", SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(admin_dashboard.bp)
        self.app.register_blueprint(bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        with db.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        db.create_all()
        self.user = User(email="private-one@example.test", school="School A", name="Hidden Name", email_verified=True)
        self.other = User(email="private-two@example.test", school="School B", name="Other Student", email_verified=True)
        db.session.add_all([self.user, self.other])
        db.session.commit()
        self.client = self.app.test_client()
        self.login(self.user)
        self.admin_patch = patch.object(admin_dashboard, "ADMIN_SECRET", "admin-test-secret")
        self.admin_patch.start()

    def tearDown(self):
        self.admin_patch.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, user):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user.id
            session["community_csrf"] = "test-csrf"

    def admin_login(self):
        with self.client.session_transaction() as session:
            session["admin_fingerprint"] = admin_dashboard._admin_fingerprint()
            session["admin_signed_at"] = time.time()
            session["admin_csrf"] = "admin-csrf"

    def submit(self, url, **data):
        return self.client.post(url, data={"csrf":"test-csrf", **data})

    def post(self, **overrides):
        fields = dict(author_id=self.user.id, school=self.user.school, category="campus",
                      title="Campus afternoon", body="A quiet afternoon on campus")
        fields.update(overrides)
        entry = Entry(**fields)
        db.session.add(entry)
        db.session.commit()
        return entry

    def moderate(self, entry, action, **kwargs):
        self.admin_login()
        return self.client.post(f"/admin/community/entries/{entry.id}",
                                data={"csrf":"admin-csrf", "action":action, "reason":"test reason", **kwargs})

    def test_guest_reads_public_only_and_cannot_write(self):
        public = self.post()
        hidden = self.post(status="hidden")
        pending = self.post(status="pending")
        with self.client.session_transaction() as session:
            session.clear()
        self.assertEqual(self.client.get("/community").status_code, 200)
        response = self.client.get(f"/community/posts/{public.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("登录收藏", response.get_data(as_text=True))
        self.assertNotIn('data-community-action="reaction"', response.get_data(as_text=True))
        for post in (hidden, pending):
            self.assertEqual(self.client.get(f"/community/posts/{post.id}").status_code, 404)
        for url in ("/community?view=mine", "/community?view=saved", "/community/new"):
            self.assertEqual(self.client.get(url).status_code, 302)
        for url in ("/community/new", f"/community/posts/{public.id}/reaction",
                    f"/community/posts/{public.id}/comments", f"/community/entries/{public.id}/report",
                    f"/community/entries/{public.id}/delete"):
            self.assertEqual(self.submit(url).status_code, 401)
        self.assertEqual(Reaction.query.count(), 0)
        self.assertEqual(Report.query.count(), 0)
        self.assertEqual(Entry.query.count(), 3)

    def test_guest_preview_is_limited_to_three_posts(self):
        outsider = User(email="never-posted@example.test", school="School C", name="Silent", email_verified=True)
        db.session.add(outsider)
        for index in range(5):
            self.post(title=f"Preview {index}", body="enough body text for the guest excerpt preview card")
        with self.client.session_transaction() as session:
            session.clear()
        html = self.client.get("/community").get_data(as_text=True)
        self.assertIn("Preview 4", html)
        self.assertIn("Preview 2", html)
        self.assertNotIn("Preview 1", html)
        self.assertNotIn("Preview 0", html)
        self.assertIn("还有 2 条动态", html)
        self.assertNotIn("下一页", html)
        self.assertNotIn("School C", html)
        newest = Entry.query.filter_by(title="Preview 4").one()
        older = Entry.query.filter_by(title="Preview 0").one()
        self.assertEqual(self.client.get(f"/community/posts/{newest.id}").status_code, 200)
        self.assertEqual(self.client.get(f"/community/posts/{older.id}").status_code, 403)
        self.login(self.user)
        full = self.client.get("/community").get_data(as_text=True)
        self.assertIn("Preview 0", full)
        self.assertIn("School A", full)
        self.assertNotIn("School C", full)

    def test_async_reactions_and_errors(self):
        post = self.post()
        url = f"/community/posts/{post.id}/reaction"
        headers = {"Accept": "application/json"}
        for enabled, count in [("1", 1), ("1", 1), ("0", 0)]:
            response = self.client.post(url, headers=headers, data={
                "csrf": "test-csrf", "kind": "like", "enabled": enabled})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {"enabled": enabled == "1", "likes": count})
        response = self.client.post(url, headers=headers, data={"kind": "save", "enabled": "1"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.json)
        self.assertEqual(Reaction.query.count(), 0)
        response = self.client.post(f"/community/entries/{post.id}/report", headers=headers,
            data={"csrf": "test-csrf", "reason": "test report"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)
        self.assertEqual(Report.query.count(), 1)

    def test_login_and_verified_email_required(self):
        with self.client.session_transaction() as session:
            session.clear()
        self.assertEqual(self.client.get("/community").status_code, 200)
        self.assertEqual(self.submit("/community/new").status_code, 401)
        self.login(self.user)
        self.user.email_verified = False
        db.session.commit()
        self.assertEqual(self.client.get("/community").status_code, 200)

    def test_csrf_and_invalid_input_do_not_write(self):
        self.assertEqual(self.client.post("/community/new", data={}).status_code, 400)
        for category, title, body in [("invalid", "Title", "Hello world"), ("campus", "a", "body content"),
                                      ("campus", "Title", "x"*2001)]:
            self.assertEqual(self.submit("/community/new",category=category,title=title,body=body).status_code,400)
        self.assertEqual(Entry.query.count(),0)

    def test_confession_requires_review_and_owner_can_view(self):
        self.assertEqual(self.submit("/community/new",category="confession",title="A confession",body="A kind classmate",anonymous="1").status_code,302)
        post = Entry.query.one()
        self.assertEqual(post.status,"pending")
        self.assertEqual(self.client.get(f"/community/posts/{post.id}").status_code,200)
        self.login(self.other)
        self.assertEqual(self.client.get(f"/community/posts/{post.id}").status_code,404)
        self.assertNotIn("A confession",self.client.get("/community").get_data(as_text=True))
        self.moderate(post,"approve")
        self.assertEqual(self.client.get(f"/community/posts/{post.id}").status_code,200)

    def test_anonymous_does_not_expose_name_or_email_and_html_is_escaped(self):
        post = self.post(anonymous=True)
        post.body = "<script>alert('x')</script>"
        db.session.commit()
        self.login(self.other)
        html = self.client.get(f"/community/posts/{post.id}").get_data(as_text=True)
        self.assertNotIn("Hidden Name",html)
        self.assertNotIn("private-one",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>alert",html)

    def test_persistent_post_and_comment_limits(self):
        data=dict(category="campus",title="A new topic",body="Today is sunny")
        self.assertEqual(self.submit("/community/new",**data).status_code,302)
        self.assertEqual(self.submit("/community/new",**data).status_code,429)
        post=Entry.query.one()
        self.assertEqual(self.submit(f"/community/posts/{post.id}/comments",body="hello").status_code,302)
        self.assertEqual(self.submit(f"/community/posts/{post.id}/comments",body="again").status_code,429)
        self.assertEqual(Entry.query.filter_by(parent_id=post.id).count(),1)

    def test_likes_and_saves_are_idempotent_and_personal(self):
        post=self.post()
        for kind in ("like","save"):
            for _ in range(2):
                self.assertEqual(self.submit(f"/community/posts/{post.id}/reaction",kind=kind,enabled="1").status_code,302)
        self.assertEqual(Reaction.query.count(),2)
        self.assertIn(post.title,self.client.get("/community?view=saved").get_data(as_text=True))
        self.login(self.other)
        self.assertNotIn(post.title,self.client.get("/community?view=saved").get_data(as_text=True))
        self.login(self.user)
        self.submit(f"/community/posts/{post.id}/reaction",kind="like",enabled="0")
        self.assertEqual(Reaction.query.filter_by(kind="like").count(),0)

    def test_cannot_delete_someone_elses_post(self):
        post=self.post()
        self.login(self.other)
        self.assertEqual(self.submit(f"/community/entries/{post.id}/delete").status_code,404)
        self.assertIsNotNone(db.session.get(Entry,post.id))

    def test_reports_deduplicate_and_admin_resolves(self):
        post=self.post()
        self.login(self.other)
        for _ in range(2):
            self.assertEqual(self.submit(f"/community/entries/{post.id}/report",reason="personal information").status_code,302)
        self.assertEqual(Report.query.count(),1)
        self.assertEqual(self.client.get("/admin/community").status_code,302)
        self.admin_login()
        html=self.client.get("/admin/community?state=reports").get_data(as_text=True)
        self.assertIn("personal information",html)
        self.moderate(post,"hide")
        self.assertTrue(Report.query.one().resolved)
        self.assertEqual(self.client.get(f"/community/posts/{post.id}").status_code,404)
        self.assertEqual(Audit.query.count(),1)

    def test_admin_csrf_reason_and_pin_validation(self):
        post=self.post(status="pending")
        self.admin_login()
        self.assertEqual(self.client.post(f"/admin/community/entries/{post.id}",data={"action":"approve"}).status_code,400)
        self.assertEqual(self.moderate(post,"approve",reason="").status_code,400)
        self.assertEqual(self.moderate(post,"pin").status_code,400)
        self.moderate(post,"approve")
        self.moderate(post,"pin")
        self.assertTrue(db.session.get(Entry,post.id).pinned)
        self.moderate(post,"hide")
        self.assertFalse(db.session.get(Entry,post.id).pinned)

    def test_muted_user_cannot_post_comment_or_like_but_can_report(self):
        post=self.post()
        self.assertEqual(self.submit(f"/community/entries/{post.id}/report",reason="harassment").status_code,302)
        self.moderate(post,"ban")
        self.assertEqual(db.session.get(Entry,post.id).status,"hidden")
        self.login(self.other)
        self.assertEqual(self.client.get(f"/community/posts/{post.id}").status_code,404)
        self.login(self.user)
        self.assertEqual(self.submit("/community/new",category="campus",title="hello",body="hello world").status_code,403)
        self.assertEqual(self.submit(f"/community/posts/{post.id}/comments",body="hello").status_code,403)
        self.assertEqual(self.submit(f"/community/posts/{post.id}/reaction",kind="like",enabled="1").status_code,403)
        self.moderate(post,"unban")
        self.assertEqual(db.session.get(Entry,post.id).status,"hidden")
        self.moderate(post,"approve")
        self.assertEqual(self.submit(f"/community/posts/{post.id}/comments",body="hello").status_code,302)

    def test_confession_comments_require_review(self):
        post=self.post(category="confession",status="published",title="A confession",body="A kind classmate")
        self.login(self.other)
        self.assertEqual(self.submit(f"/community/posts/{post.id}/comments",body="hello there").status_code,302)
        comment=Entry.query.filter_by(parent_id=post.id).one()
        self.assertEqual(comment.status,"pending")
        self.login(self.user)
        html=self.client.get(f"/community/posts/{post.id}").get_data(as_text=True)
        self.assertNotIn("hello there",html)
        self.login(self.other)
        self.assertIn("hello there",self.client.get(f"/community/posts/{post.id}").get_data(as_text=True))
        self.moderate(comment,"approve")
        self.login(self.user)
        self.assertIn("hello there",self.client.get(f"/community/posts/{post.id}").get_data(as_text=True))

    def test_post_delete_keeps_reports_and_audit(self):
        post=self.post()
        comment=Entry(author_id=self.other.id,parent_id=post.id,school="School B",category="campus",body="reply")
        db.session.add(comment)
        db.session.flush()
        db.session.add_all([Reaction(user_id=self.other.id,entry_id=post.id,kind="like"),
                            Report(user_id=self.other.id,entry_id=comment.id,reason="test"),
                            Audit(entry_id=post.id,action="approve",reason="test")])
        db.session.commit()
        self.assertEqual(self.submit(f"/community/entries/{post.id}/delete").status_code,302)
        leftover=Entry.query.filter_by(id=post.id).one()
        self.assertEqual(leftover.status,"deleted")
        self.assertEqual(leftover.body,"")
        self.assertEqual(Reaction.query.count(),0)
        self.assertEqual(Report.query.count(),1)
        self.assertTrue(Report.query.one().resolved)
        self.assertGreaterEqual(Audit.query.count(),2)
        self.assertEqual(self.client.get(f"/community/posts/{post.id}").status_code,404)

    def test_expired_ban_allows_comment(self):
        post=self.post()
        db.session.add(Ban(user_id=self.user.id,until=datetime.utcnow()-timedelta(seconds=1),reason="test"))
        db.session.commit()
        self.assertEqual(self.submit(f"/community/posts/{post.id}/comments",body="hello").status_code,302)

    def test_hidden_parent_blocks_comment_and_interactions(self):
        post=self.post(status="hidden")
        for action,data in [("comments",{"body":"hello"}),("reaction",{"kind":"like","enabled":"1"})]:
            self.assertEqual(self.submit(f"/community/posts/{post.id}/{action}",**data).status_code,403)
        self.login(self.other)
        self.assertEqual(self.submit(f"/community/posts/{post.id}/comments",body="hello").status_code,404)

    def test_account_purge_removes_owned_activity_and_preserves_other_posts(self):
        post=self.post()
        other_post=Entry(author_id=self.other.id,school="School B",category="campus",title="Other",body="other post")
        db.session.add(other_post)
        db.session.flush()
        db.session.add_all([Entry(author_id=self.user.id,parent_id=other_post.id,school="School A",category="campus",body="reply"),
                           Reaction(user_id=self.user.id,entry_id=other_post.id,kind="save"),
                           Report(user_id=self.user.id,entry_id=other_post.id,reason="test"),
                           Ban(user_id=self.user.id,until=datetime.utcnow(),reason="test"),
                           Limit(user_id=self.user.id,action="post",last_at=datetime.utcnow()),
                           Audit(entry_id=post.id,user_id=self.user.id,action="ban",reason="test")])
        db.session.commit()
        purge_community(self.user.id)
        db.session.delete(self.user)
        db.session.commit()
        self.assertEqual(Entry.query.count(),1)
        self.assertEqual(Entry.query.one().id,other_post.id)
        for model in (Reaction,Report,Ban,Limit):
            self.assertEqual(model.query.count(),0)
        audit=Audit.query.one()
        self.assertIsNone(audit.entry_id)
        self.assertIsNone(audit.user_id)

    def test_unban_after_author_deletes_all_posts(self):
        post=self.post()
        self.moderate(post,"ban")
        self.submit(f"/community/entries/{post.id}/delete")
        html=self.client.get("/admin/community?state=banned").get_data(as_text=True)
        self.assertIn(f"/admin/community/users/{self.user.id}/unban",html)
        response=self.client.post(f"/admin/community/users/{self.user.id}/unban",data={"csrf":"admin-csrf","reason":"appeal accepted"})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Ban.query.count(),0)

    def test_feed_filters_pagination_and_pinned_order(self):
        for number in range(23):
            db.session.add(Entry(author_id=self.user.id,school="School A",category="campus",title=f"Topic {number:02}",body="hello"))
        db.session.commit()
        first=Entry.query.order_by(Entry.id).first()
        first.pinned=True
        db.session.commit()
        html=self.client.get("/community").get_data(as_text=True)
        self.assertLess(html.index("Topic 00"),html.index("Topic 22"))
        self.assertIn("下一页",html)
        self.assertNotIn("Topic 00",self.client.get("/community?page=2").get_data(as_text=True))
        self.assertNotIn("Topic",self.client.get("/community?school=School+B").get_data(as_text=True))
        self.assertEqual(self.client.get("/community?category=invalid").status_code,400)
