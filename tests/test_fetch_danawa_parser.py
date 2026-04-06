from pathlib import Path
import sys
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_danawa  # noqa: E402


class ParserTests(unittest.TestCase):
    def test_parse_detail_specs_prefers_structured_pd(self):
        html = Path(__file__).with_name("fixtures").joinpath("detail_spec_sample.html").read_text(encoding="utf-8")
        pd_watt, vesa, image_url = fetch_danawa.parse_detail_specs(html)
        self.assertEqual(pd_watt, 90)
        self.assertEqual(vesa, "100x100")
        self.assertEqual(image_url, "https://img.example.com/a.jpg")

    def test_parse_usb_c_pd_watt_ignores_power_consumption(self):
        text = "usb-c 지원 / 소비전력 90W / 어댑터 120W"
        self.assertIsNone(fetch_danawa.parse_usb_c_pd_watt(text.lower()))

    def test_parse_image_url_attribute_order_independent(self):
        html = '<meta content="//cdn.example.com/og.jpg" property="og:image" />'
        self.assertEqual(fetch_danawa.parse_image_url(html), "https://cdn.example.com/og.jpg")

    def test_parse_image_url_uses_twitter_before_body_image(self):
        html = (
            '<meta name="twitter:image" content="https://cdn.example.com/tw.jpg" />'
            '<img class="prod_img" src="https://cdn.example.com/body.jpg" />'
        )
        self.assertEqual(fetch_danawa.parse_image_url(html), "https://cdn.example.com/tw.jpg")


if __name__ == "__main__":
    unittest.main()
