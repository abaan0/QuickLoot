import unittest

from quickloot.sources import parse_preview

SAMPLE = '''
<html><body>
<div class="tgme_widget_message" data-post="dealztrendz/100">
  <div class="tgme_widget_message_text">Swiggy Instamart Loot: <b>Amul Cake</b> ₹54
    <a href="https://instamart.in/item/ABC?share=true">Buy now</a>
  </div>
  <a class="tgme_widget_message_date"><time datetime="2026-11-19T17:00:00+00:00"></time></a>
</div>
<div class="tgme_widget_message" data-post="dealztrendz/101">
  <div class="tgme_widget_message_text">Air fryer ₹1</div>
</div>
</body></html>
'''


class SourceParserTests(unittest.TestCase):
    def test_extract_posts(self):
        posts = parse_preview(SAMPLE, "dealztrendz")
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0].post_url, "https://t.me/dealztrendz/100")
        self.assertEqual(posts[0].offer_url, "https://instamart.in/item/ABC?share=true")
        self.assertEqual(posts[0].published_at.year, 2026)
        self.assertIn("Amul Cake", posts[0].text)
        self.assertEqual(posts[1].offer_url, None)

    def test_no_messages(self):
        self.assertEqual(parse_preview("<html></html>", "test"), [])


if __name__ == "__main__":
    unittest.main()
