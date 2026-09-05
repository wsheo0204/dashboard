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

    def test_parse_detail_specs_mobile_like_pd_and_lazy_image(self):
        html = """
        <ul class="spec_list">
          <li><span class="tit">USB-C</span><span class="txt">PD 충전 최대 65와트</span></li>
        </ul>
        <img class="swiper-lazy" data-original="//cdn.example.com/mobile-main.jpg" />
        """
        pd_watt, _, image_url = fetch_danawa.parse_detail_specs(html)
        self.assertEqual(pd_watt, 65)
        self.assertEqual(image_url, "https://cdn.example.com/mobile-main.jpg")

    def test_parse_image_url_from_json_ld(self):
        html = '<script type="application/ld+json">{"image":"https:\\/\\/cdn.example.com\\/json.jpg"}</script>'
        self.assertEqual(fetch_danawa.parse_image_url(html), "https://cdn.example.com/json.jpg")

    def test_parse_image_url_resolves_relative_path_with_base_url(self):
        html = '<meta property="og:image" content="/images/product-main.jpg" />'
        self.assertEqual(
            fetch_danawa.parse_image_url(html, base_url="https://prod.danawa.com/info/?pcode=123"),
            "https://prod.danawa.com/images/product-main.jpg",
        )

    def test_parse_detail_specs_resolves_body_image_relative_path(self):
        html = '<img class="prod_img" src="../img/main.jpg" />'
        _, _, image_url = fetch_danawa.parse_detail_specs(
            html,
            base_url="https://prod.danawa.com/info/?pcode=123",
        )
        self.assertEqual(image_url, "https://prod.danawa.com/img/main.jpg")

    def test_parse_products_excludes_overseas_items(self):
        html = """
        <ul>
          <li class="prod_item">
            <p class="prod_name"><a href="https://prod.danawa.com/info/?pcode=1">국내 모델 27인치 4K USB-C</a></p>
            <div class="price_sect"><strong>300,000</strong></div>
            <div class="prod_spec_set">27인치 / 3840x2160 / USB-C</div>
          </li>
          <li class="prod_item">
            <p class="prod_name"><a href="https://prod.danawa.com/info/?pcode=2">해외구매 모델 27인치 4K USB-C</a></p>
            <div class="price_sect"><strong>310,000</strong></div>
            <div class="prod_spec_set">27인치 / 3840x2160 / USB-C / 해외구매</div>
          </li>
        </ul>
        """
        parsed = fetch_danawa.parse_products(html)
        self.assertEqual(len(parsed), 1)
        self.assertIn("국내 모델", parsed[0]["name"])

    def test_parse_detail_specs_extracts_pd_from_script_json(self):
        html = """
        <script>
          window.__STATE__ = {
            "pd충전":"최대 65W"
          };
        </script>
        """
        pd_watt, _, _ = fetch_danawa.parse_detail_specs(html)
        self.assertEqual(pd_watt, 65)


if __name__ == "__main__":
    unittest.main()
