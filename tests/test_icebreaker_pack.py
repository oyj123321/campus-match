"""破冰扩展包：默认关闭；开通后只加 3 句问卷开场白，不改配对。差异免费。"""

import json
import os
import tempfile
import unittest

_fd, _DB_PATH = tempfile.mkstemp(prefix="cm-ice-pack-", suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH
os.environ["MAIL_ENABLED"] = "false"
os.environ["ICEBREAKER_PACK_ENABLED"] = "false"
os.environ["ICEBREAKER_PACK_MOCK_GRANT"] = "false"
os.environ["ADMIN_SECRET"] = "test-admin-secret"
os.environ["SECRET_KEY"] = "test-secret-key"
for _key in (
    "ALIPAY_APP_ID",
    "ALIPAY_APP_PRIVATE_KEY",
    "ALIPAY_PUBLIC_KEY",
):
    os.environ.pop(_key, None)

from app import app, _purge_user_account
from icebreaker_pack import (
    ALIPAY_PRODUCT,
    PACK_PRICE_CENTS,
    PACK_PRICE_LABEL,
    build_match_openers,
    icebreaker_pack_enabled,
)
from icebreakers import pick_icebreakers
from models import IcebreakerPackEntitlement, IcebreakerPackOrder, Match, User, db

DIFF = "「作息」差异较大（你偏「早睡」方向，对方偏「晚睡」方向）——见面时多问问对方真实习惯"
ICE = ["自定义甲话题，想听你说说", "自定义乙话题，周末去哪", "自定义丙话题，食堂窗口"]
FORBIDDEN = (
    "优先匹配", "更高契合", "保证聊得上", "解锁联系方式",
    "優先匹配", "更高契合", "保證聊得上", "解鎖聯繫方式", "解鎖聯絡方式",
)
ALIPAY_KEYS = (
    "ALIPAY_APP_ID",
    "ALIPAY_APP_PRIVATE_KEY",
    "ALIPAY_PUBLIC_KEY",
)


class IcebreakerPackTests(unittest.TestCase):
    def setUp(self):
        os.environ["ICEBREAKER_PACK_ENABLED"] = "false"
        os.environ["ICEBREAKER_PACK_MOCK_GRANT"] = "false"
        for key in ALIPAY_KEYS:
            os.environ.pop(key, None)
        app.config["TESTING"] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.viewer = self._user(1, "female")
        self.partner = self._user(2, "male")
        self.other = self._user(3, "female")
        insight = {
            "summary": "找到 1 处相近、1 处差异。",
            "strengths": ["都喜欢散步"],
            "differences": [DIFF],
            "icebreakers": list(ICE),
            "shared_tags": ["科幻/奇幻"],
            "total_differences": 1,
        }
        self.raw_insight = json.dumps(insight, ensure_ascii=False)
        self.match = Match(
            user1_id=self.viewer.id,
            user2_id=self.partner.id,
            score=0.42,
            mode="batch",
            active=True,
            insight_json=self.raw_insight,
        )
        self.viewer.answers = {
            9: 1, 11: 5, 25: ["科幻/奇幻", "喜剧"], 5: 1,
        }
        self.partner.answers = {
            9: 5, 11: 1, 25: ["科幻/奇幻"], 5: 5,
        }
        db.session.add(self.match)
        db.session.commit()
        self.client = app.test_client()
        self.partner_client = app.test_client()
        self.other_client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.viewer.id
        with self.partner_client.session_transaction() as sess:
            sess["user_id"] = self.partner.id
        with self.other_client.session_transaction() as sess:
            sess["user_id"] = self.other.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _user(self, n, gender):
        user = User(
            school="澳门大学",
            email=f"ice{n}@um.edu.mo",
            email_verified=True,
            name=f"同学{n}",
            gender=gender,
            looking_for="both",
            education_level="bachelor",
            wechat_id=f"wx-{n}",
            open_to_match=True,
        )
        db.session.add(user)
        db.session.flush()
        return user

    def _cards(self, client=None):
        response = (client or self.client).get("/api/matches")
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()["matches"]

    def _assert_pair_untouched(self):
        db.session.refresh(self.match)
        db.session.refresh(self.viewer)
        db.session.refresh(self.partner)
        self.assertEqual(self.match.score, 0.42)
        self.assertEqual((self.match.user1_id, self.match.user2_id), (self.viewer.id, self.partner.id))
        self.assertEqual(self.match.insight_json, self.raw_insight)
        self.assertEqual(self.match.active, True)
        self.assertEqual(self.partner.wechat_id, "wx-2")
        self.assertEqual(self.partner.email, "ice2@um.edu.mo")
        self.assertEqual(self.viewer.wechat_id, "wx-1")

    def test_default_flag_off_and_price(self):
        os.environ.pop("ICEBREAKER_PACK_ENABLED", None)
        self.assertFalse(icebreaker_pack_enabled())
        self.assertEqual(PACK_PRICE_CENTS, 660)
        self.assertEqual(PACK_PRICE_LABEL, "¥6.6")

    def test_flag_off_keeps_the_old_card(self):
        card = self._cards()[0]
        self.assertNotIn("icebreaker_pack", card)
        self.assertNotIn("match_id", card)
        self.assertNotIn("openers", card)
        self.assertEqual(card["icebreakers"], ICE)
        self.assertEqual(card["differences"], [DIFF])
        self.assertEqual(card["id"], self.partner.id)
        self.assertEqual(card["wechat_id"], "wx-2")
        self.assertEqual(card["email"], "ice2@um.edu.mo")
        self.assertNotIn("score", card)
        checkout = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/checkout")
        self.assertEqual(checkout.status_code, 404)
        mock = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/mock-grant")
        self.assertEqual(mock.status_code, 404)
        self.assertEqual(IcebreakerPackOrder.query.count(), 0)
        self._assert_pair_untouched()

    def test_flag_on_locked_keeps_free_diffs_and_hides_openers(self):
        os.environ["ICEBREAKER_PACK_ENABLED"] = "true"
        card = self._cards()[0]
        self.assertTrue(card["icebreaker_pack"]["enabled"])
        self.assertFalse(card["icebreaker_pack"]["entitled"])
        self.assertFalse(card["icebreaker_pack"]["mock_grant"])
        self.assertEqual(card["icebreaker_pack"]["price_cents"], 660)
        self.assertEqual(card["icebreaker_pack"]["price_label"], "¥6.6")
        self.assertEqual(card["icebreaker_pack"]["pay_provider"], "alipay")
        self.assertEqual(card["icebreaker_pack"]["pay_product"], ALIPAY_PRODUCT)
        self.assertEqual(card["match_id"], self.match.id)
        self.assertEqual(card["icebreakers"], ICE)
        self.assertTrue(all(isinstance(line, str) for line in card["icebreakers"]))
        self.assertEqual(card["openers"], [])
        self.assertEqual(card["differences"], [DIFF])
        self.assertEqual(card["differences_count"], 1)
        self.assertNotIn("我更靠近早睡", json.dumps(card, ensure_ascii=False))
        self.assertEqual(card["id"], self.partner.id)
        self.assertEqual(card["wechat_id"], "wx-2")
        self._assert_pair_untouched()

    def test_checkout_and_notify_do_not_charge_or_grant(self):
        os.environ["ICEBREAKER_PACK_ENABLED"] = "true"
        checkout = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/checkout")
        self.assertEqual(checkout.status_code, 503)
        body = checkout.get_json()
        self.assertEqual(body["payment"], "noop")
        self.assertEqual(body["provider"], "alipay")
        self.assertEqual(body["product"], ALIPAY_PRODUCT)
        self.assertEqual(body["reason"], "unconfigured")
        self.assertIn("支付宝", body["error"])
        self.assertFalse(body["ok"])
        os.environ["ALIPAY_APP_ID"] = "2021000000000000"
        partial = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/checkout")
        self.assertEqual(partial.status_code, 503)
        self.assertEqual(partial.get_json()["reason"], "unconfigured")
        os.environ.pop("ALIPAY_APP_ID", None)
        notify = self.client.post(
            "/api/pay/alipay/icebreaker-pack/notify",
            data={"trade_status": "TRADE_SUCCESS", "out_trade_no": "x"},
        )
        self.assertEqual(notify.status_code, 503)
        self.assertEqual(notify.get_json()["payment"], "noop")
        self.assertEqual(notify.get_json()["provider"], "alipay")
        gone = self.client.post("/api/pay/wechat/icebreaker-pack/notify", json={"trade_state": "SUCCESS"})
        self.assertEqual(gone.status_code, 404)
        for key, value in zip(ALIPAY_KEYS, ("2021000000000000", "test-private-key", "test-public-key")):
            os.environ[key] = value
        wired = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/checkout")
        self.assertEqual(wired.status_code, 503)
        self.assertEqual(wired.get_json()["reason"], "not_wired")
        self.assertEqual(wired.get_json()["payment"], "noop")
        self.assertEqual(wired.get_json()["product"], "alipay.trade.wap.pay")
        notified = self.client.post(
            "/api/pay/alipay/icebreaker-pack/notify",
            data={"trade_status": "TRADE_SUCCESS", "total_amount": "6.60"},
        )
        self.assertEqual(notified.status_code, 200)
        self.assertEqual(notified.get_json()["payment"], "noop")
        self.assertEqual(notified.get_json()["reason"], "not_wired")
        self.assertEqual(notified.get_json()["provider"], "alipay")
        self.assertEqual(IcebreakerPackOrder.query.count(), 0)
        self.assertEqual(IcebreakerPackEntitlement.query.count(), 0)
        stranger = self.other_client.post(f"/api/matches/{self.match.id}/icebreaker-pack/checkout")
        self.assertEqual(stranger.status_code, 404)
        self._assert_pair_untouched()

    def test_mock_grant_expands_same_card_and_persists(self):
        os.environ["ICEBREAKER_PACK_ENABLED"] = "true"
        os.environ["ICEBREAKER_PACK_MOCK_GRANT"] = "false"
        denied = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/mock-grant")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(IcebreakerPackEntitlement.query.count(), 0)

        os.environ["ICEBREAKER_PACK_MOCK_GRANT"] = "true"
        granted = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/mock-grant")
        self.assertEqual(granted.status_code, 200, granted.get_json())
        self.assertTrue(granted.get_json()["entitled"])
        self.assertFalse(granted.get_json()["already"])
        again = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/mock-grant")
        self.assertTrue(again.get_json()["already"])
        self.assertEqual(IcebreakerPackEntitlement.query.count(), 1)
        self.assertEqual(IcebreakerPackOrder.query.count(), 1)
        self.assertEqual(IcebreakerPackOrder.query.one().provider, "mock")
        self.assertEqual(IcebreakerPackOrder.query.one().status, "granted")
        self.assertEqual(IcebreakerPackOrder.query.one().amount_cents, 660)

        first = self._cards()[0]
        second = self._cards()[0]
        self.assertEqual(first["icebreakers"], second["icebreakers"])
        self.assertEqual(first["icebreakers"], ICE)
        self.assertEqual(first["openers"], second["openers"])
        self.assertEqual(len(first["openers"]), 3)
        sends = [item["send"] for item in first["openers"]]
        self.assertEqual(len(set(sends)), 3)
        self.assertIn("科幻/奇幻", sends[0])
        self.assertIn("我更靠近早睡", sends[1])
        self.assertIn("夜猫子", sends[1])
        self.assertIn("几乎不运动", sends[2])
        self.assertNotIn("结婚", "\n".join(sends))
        self.assertNotIn("婚姻", "\n".join(sends))
        pool = pick_icebreakers(
            shared_tags=["科幻/奇幻"], seed=(self.viewer.id, self.partner.id), n=12,
            my_school="澳门大学", their_school="澳门大学",
        )
        for send in sends:
            self.assertNotIn(send, pool)
            self.assertNotIn(send, ICE)
        self.assertTrue(all(item.get("tip") and item.get("send") for item in first["openers"]))
        self.assertEqual(first["differences"], [DIFF])
        self.assertTrue(first["icebreaker_pack"]["entitled"])
        self.assertFalse(first["icebreaker_pack"]["mock_grant"])
        self.assertEqual(first["id"], self.partner.id)
        self.assertEqual(first["email"], "ice2@um.edu.mo")
        self.assertEqual(first["wechat_id"], "wx-2")

        partner_card = self._cards(self.partner_client)[0]
        self.assertEqual(partner_card["icebreakers"], ICE)
        self.assertEqual(partner_card["openers"], [])
        self.assertEqual(partner_card["differences"], [DIFF])
        self.assertFalse(partner_card["icebreaker_pack"]["entitled"])
        self.assertEqual(partner_card["id"], self.viewer.id)

        os.environ["ICEBREAKER_PACK_ENABLED"] = "false"
        hidden = self._cards()[0]
        self.assertNotIn("icebreaker_pack", hidden)
        self.assertEqual(hidden["icebreakers"], ICE)
        self.assertEqual(hidden["differences"], [DIFF])
        self._assert_pair_untouched()

    def test_admin_grant_is_per_viewer(self):
        response = self.client.post(
            "/api/admin/icebreaker-pack/grant",
            json={"match_id": self.match.id, "user_id": self.partner.id},
        )
        self.assertEqual(response.status_code, 403)
        ok = self.client.post(
            "/api/admin/icebreaker-pack/grant",
            json={"match_id": self.match.id, "user_id": self.partner.id},
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        self.assertEqual(ok.status_code, 200, ok.get_json())
        self.assertEqual(ok.get_json()["provider"], "admin")
        missing = self.client.post(
            "/api/admin/icebreaker-pack/grant",
            json={"match_id": self.match.id, "user_id": self.other.id},
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        self.assertEqual(missing.status_code, 404)
        os.environ["ICEBREAKER_PACK_ENABLED"] = "true"
        buyer = self._cards()[0]
        partner = self._cards(self.partner_client)[0]
        self.assertFalse(buyer["icebreaker_pack"]["entitled"])
        self.assertEqual(len(buyer["icebreakers"]), 3)
        self.assertEqual(buyer["openers"], [])
        self.assertEqual(buyer["differences"], [DIFF])
        self.assertTrue(partner["icebreaker_pack"]["entitled"])
        self.assertEqual(len(partner["icebreakers"]), 3)
        self.assertEqual(len(partner["openers"]), 3)
        self.assertIn("我更靠近夜猫子", partner["openers"][1]["send"])
        self.assertEqual(partner["differences"], [DIFF])
        repeat = self.client.post(
            "/api/admin/icebreaker-pack/grant",
            json={"match_id": self.match.id, "user_id": self.partner.id},
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        self.assertTrue(repeat.get_json()["already"])
        self.assertEqual(IcebreakerPackEntitlement.query.count(), 1)
        self._assert_pair_untouched()

    def test_inactive_match_cannot_be_granted(self):
        os.environ["ICEBREAKER_PACK_ENABLED"] = "true"
        os.environ["ICEBREAKER_PACK_MOCK_GRANT"] = "true"
        self.match.active = False
        db.session.commit()
        mock = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/mock-grant")
        checkout = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/checkout")
        self.assertEqual(mock.status_code, 400)
        self.assertEqual(checkout.status_code, 400)
        self.assertEqual(IcebreakerPackEntitlement.query.count(), 0)
        listed = self.client.get("/api/matches?all=1")
        card = listed.get_json()["matches"][0]
        self.assertNotIn("icebreaker_pack", card)
        self.assertIsNone(card["email"])
        self.assertIsNone(card["wechat_id"])

    def test_purge_drops_pack_rows(self):
        os.environ["ICEBREAKER_PACK_ENABLED"] = "true"
        os.environ["ICEBREAKER_PACK_MOCK_GRANT"] = "true"
        granted = self.client.post(f"/api/matches/{self.match.id}/icebreaker-pack/mock-grant")
        self.assertEqual(granted.status_code, 200, granted.get_json())
        _purge_user_account(self.viewer)
        db.session.commit()
        self.assertIsNone(db.session.get(User, self.viewer.id))
        self.assertEqual(IcebreakerPackEntitlement.query.count(), 0)
        self.assertEqual(IcebreakerPackOrder.query.count(), 0)
        self.assertIsNotNone(db.session.get(User, self.partner.id))

    def test_openers_come_from_answers_and_tags_not_the_static_pool(self):
        mine = {9: 1, 11: 5, 25: ["科幻/奇幻"], 5: 1}
        theirs = {9: 5, 11: 1, 25: ["科幻/奇幻"], 5: 5}
        first = build_match_openers(mine, theirs, ["科幻/奇幻"], seed=(4, 8), avoid=ICE)
        second = build_match_openers(mine, theirs, ["科幻/奇幻"], seed=(4, 8), avoid=ICE)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        sends = [item["send"] for item in first]
        self.assertIn("科幻/奇幻", sends[0])
        self.assertIn("我更靠近早睡", sends[1])
        self.assertIn("夜猫子", sends[1])
        self.assertIn("几乎不运动", sends[2])
        blob = "\n".join(sends)
        for banned in ("结婚", "婚姻", "出轨", "吸烟", "前任"):
            self.assertNotIn(banned, blob)
        pool = pick_icebreakers(
            shared_tags=["科幻/奇幻"], seed=(4, 8), n=12,
            my_school="澳门大学", their_school="澳门大学",
        )
        for send in sends:
            self.assertNotIn(send, pool)
        swapped = build_match_openers(theirs, mine, ["科幻/奇幻"], seed=(8, 4), avoid=ICE)
        self.assertIn("我更靠近夜猫子", swapped[1]["send"])
        self.assertNotIn("我更靠近早睡", swapped[1]["send"])

        same_side = build_match_openers({9: 1, 10: 5}, {9: 2, 10: 4}, [], seed=1)
        self.assertIn("都更靠近早睡", same_side[0]["send"])
        self.assertIn("都更靠近无辣不欢", same_side[1]["send"])
        self.assertIn("问卷上能对上的具体点不多", same_side[2]["send"])

        sparse = build_match_openers({}, {}, ["喜剧"], seed=3)
        self.assertIn("喜剧", sparse[0]["send"])
        self.assertEqual(len(sparse), 3)
        avoided = build_match_openers({}, {}, ["喜剧"], seed=3, avoid=[sparse[0]["send"]])
        self.assertNotIn(sparse[0]["send"], [item["send"] for item in avoided])
        self.assertEqual(len(avoided), 3)

        empty = build_match_openers({}, {}, [], seed=1)
        self.assertEqual(len(empty), 3)
        self.assertEqual(len({item["send"] for item in empty}), 3)

    def test_copy_has_no_forbidden_claims(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        chunks = []
        for name in ("static/i18n.js", "i18n_server.py"):
            with open(os.path.join(root, name), encoding="utf-8") as handle:
                chunks.extend(line for line in handle if "pack." in line)
        with open(os.path.join(root, "icebreaker_pack.py"), encoding="utf-8") as handle:
            chunks.append(handle.read())
        with open(os.path.join(root, "CHANGELOG.md"), encoding="utf-8") as handle:
            log = handle.read()
        chunks.append(log[log.index("## [1.9.73]"):log.index("## [1.9.72]")])
        with open(os.path.join(root, "templates/matches.html"), encoding="utf-8") as handle:
            page = handle.read()
        self.assertIn("requestIcePack", page)
        self.assertIn("pack.note", page)
        self.assertIn("card.diff", page)
        self.assertIn("m.differences && m.differences.length", page)
        self.assertIn("pack.openersTitle", page)
        self.assertIn("m.openers", page)
        self.assertNotIn("icebreaker_pack.entitled) {\n            html += '<div class=\"box box-warn\"", page)
        joined = "\n".join(chunks)
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase, joined)
        cta_lines = [line for line in chunks if "pack.cta" in line]
        self.assertEqual(len(cta_lines), 4)
        self.assertIn("要 3 句按这次问卷写的开场白", "\n".join(cta_lines))
        self.assertNotIn("再要 3 条", "\n".join(cta_lines))
        note_lines = [line for line in chunks if "pack.note" in line]
        self.assertIn("免费的破冰话题和差异说明都还在", "\n".join(note_lines))
        self.assertEqual(joined.count("'pack.rail'"), 4)
        self.assertEqual(joined.count("'pack.openersTitle'"), 4)
        import inspect
        import icebreaker_pack as pack_mod
        source = inspect.getsource(pack_mod)
        self.assertNotIn("pick_icebreakers", source)
        self.assertNotIn("openapi.alipay.com", source)
        self.assertNotIn("weixin", source.lower())
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)
        old_bits = (
            "更多破冰话题、可复制的开场白、差异说明",
            "只增加破冰话题、可复制开场白和差异说明",
            "extra icebreakers, copyable openers, and differences",
            "mais tópicos, frases de abertura para copiar e diferenças",
        )
        for name in ("static/i18n.js", "templates/support.html", "templates/privacy.html"):
            with open(os.path.join(root, name), encoding="utf-8") as handle:
                text = handle.read()
            for bit in old_bits:
                self.assertNotIn(bit, text, name)


if __name__ == "__main__":
    unittest.main()
