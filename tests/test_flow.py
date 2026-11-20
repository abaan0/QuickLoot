import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from quickloot import __main__ as app
from quickloot.sources import DealPost


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.previous = Path.cwd()
        os.chdir(self.tempdir.name)
        self.addCleanup(lambda: os.chdir(self.previous))
        Path("config.json").write_text(json.dumps({
            "channels": ["sample"],
            "preferred_city": "Mumbai",
            "max_post_age_hours": 6,
            "max_alerts_per_run": 12,
        }), encoding="utf-8")
        self.post1 = DealPost(
            "sample/1", "sample", "Amul ice cream cake ₹54 83% OFF",
            "https://t.me/sample/1", "https://instamart.in/item/1",
            datetime.now(timezone.utc),
        )
        self.post2 = DealPost(
            "sample/2", "sample", "Blinkit: Tide detergent ₹100 deal",
            "https://t.me/sample/2", None,
            datetime.now(timezone.utc),
        )
        self.env = patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "not-a-real-bot-token",
            "TELEGRAM_CHAT_ID": "123456789",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_first_run_seeds_without_notification(self):
        with patch.object(app, "fetch_channel", return_value=[self.post1]), \
             patch.object(app, "send_telegram") as send, \
             patch("sys.argv", ["quickloot"]):
            self.assertEqual(app.main(), 0)
            send.assert_not_called()
        state = json.loads(Path("state/seen.json").read_text())
        self.assertTrue(state["initialized"])
        self.assertIn("sample/1", state["seen"])

    def test_only_new_posts_alert_and_no_repeat(self):
        with patch.object(app, "fetch_channel", return_value=[self.post1]), \
             patch.object(app, "send_telegram"), \
             patch("sys.argv", ["quickloot"]):
            app.main()
        with patch.object(app, "fetch_channel", return_value=[self.post1, self.post2]), \
             patch.object(app, "send_telegram") as send, \
             patch.object(app.time, "sleep"), \
             patch("sys.argv", ["quickloot"]):
            self.assertEqual(app.main(), 0)
            self.assertEqual(send.call_count, 1)
            self.assertIn("Household essentials", send.call_args.args[0])
        with patch.object(app, "fetch_channel", return_value=[self.post1, self.post2]), \
             patch.object(app, "send_telegram") as send, \
             patch("sys.argv", ["quickloot"]):
            self.assertEqual(app.main(), 0)
            send.assert_not_called()

    def test_cross_source_content_duplicate_not_alerted(self):
        first = DealPost("a/1", "a", "Amul ice cream cake ₹54",
                         "https://t.me/a/1", None, datetime.now(timezone.utc))
        second = DealPost("b/2", "b", "Amul ice cream cake ₹54",
                          "https://t.me/b/2", None, datetime.now(timezone.utc))
        with patch.object(app, "fetch_channel", return_value=[first]), \
             patch.object(app, "send_telegram"), \
             patch("sys.argv", ["quickloot"]):
            app.main()
        # To check a cross-source duplicate, emit first as a new alert after bootstrap,
        # then an identical second repost.
        third = DealPost("a/3", "a", first.text,
                         "https://t.me/a/3", None, datetime.now(timezone.utc))
        with patch.object(app, "fetch_channel", return_value=[third]), \
             patch.object(app, "send_telegram") as send, \
             patch.object(app.time, "sleep"), \
             patch("sys.argv", ["quickloot"]):
            app.main()
            self.assertEqual(send.call_count, 1)
        with patch.object(app, "fetch_channel", return_value=[second]), \
             patch.object(app, "send_telegram") as send, \
             patch("sys.argv", ["quickloot"]):
            app.main()
            send.assert_not_called()

    def test_html_in_post_escaped(self):
        post = DealPost("x/1", "x", "Cocoa <special> & cake ₹50",
                        "https://t.me/x/1", None, datetime.now(timezone.utc))
        message = app.render_alert(post, "Food & snacks")
        self.assertIn("&lt;special&gt;", message)
        self.assertIn("&amp; cake", message)


if __name__ == "__main__":
    unittest.main()
