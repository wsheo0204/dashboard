#!/usr/bin/env python3
"""Fetch Danawa monitor list and save filtered products to data/products.json.

This script is designed for GitHub Actions.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path

QUERIES = [
    "27인치 4k usb-c 모니터",
    "삼성 27인치 4k usb-c 모니터",
    "LG 27인치 4k usb-c 모니터",
]
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "products.json"
USER_AGENT = "Mozilla/5.0 (compatible; dashboard-bot/1.0)"
logger = logging.getLogger("fetch_danawa")


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def normalize_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    return url


def text_of(html_snippet: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_snippet)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_price(text: str) -> int | None:
    nums = re.findall(r"\d[\d,]*", text)
    if not nums:
        return None
    value = nums[0].replace(",", "")
    try:
        return int(value)
    except ValueError:
        return None


def detect_brand(name: str) -> str:
    lowered = name.lower()
    if "삼성" in name or "samsung" in lowered:
        return "Samsung"
    if "lg" in lowered or "엘지" in name:
        return "LG"
    if "알파스캔" in name:
        return "알파스캔"
    if "크로스오버" in name:
        return "크로스오버"
    return "기타"


def parse_usb_c_pd_watt(spec_text: str) -> int | None:
    invalid_nearby_keywords = [
        "소비전력",
        "정격",
        "어댑터",
        "출력 전력",
        "입력 전력",
        "전력소모",
        "소모전력",
        "소비 파워",
        "power consumption",
        "adapter",
        "ac",
    ]
    patterns = [
        r"(?:usb[\s\-]?c|type[\s\-]?c)\D{0,30}(?:pd|power\s*delivery|충전)\D{0,12}(\d{2,3})\s*(?:w|와트)?",
        r"(?:pd|power\s*delivery|usb\s*pd)\D{0,15}(\d{2,3})\s*(?:w|와트)?",
        r"(?:충전\s*출력|충전)\D{0,12}(\d{2,3})\s*(?:w|와트)?",
    ]

    lowered = spec_text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, lowered):
            try:
                watt = int(match.group(1))
            except ValueError:
                continue

            if not (10 <= watt <= 240):
                continue

            start, end = match.span()
            nearby = lowered[max(0, start - 30) : min(len(lowered), end + 30)]
            if any(keyword in nearby for keyword in invalid_nearby_keywords):
                continue

            return watt
    return None


def parse_vesa_mount(spec_text: str) -> str | None:
    match = re.search(r"(?:vesa|베사)\D{0,10}(\d{2,3})\D{0,4}x\D{0,4}(\d{2,3})", spec_text)
    if not match:
        return None
    return f"{match.group(1)}x{match.group(2)}"


def parse_image_url(detail_html: str) -> str | None:
    # 1) Meta tags (og:image, twitter:image, itemprop=image) with attribute-order invariance.
    for meta_match in re.finditer(r"<meta\s+[^>]*>", detail_html, flags=re.IGNORECASE):
        attrs = parse_tag_attributes(meta_match.group(0))
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
        if key in {"og:image", "twitter:image", "image"} and attrs.get("content"):
            return normalize_url(html.unescape(attrs["content"].strip()))

    # 2) Common image declarations beyond meta tags.
    for pattern in [
        r'<link[^>]+rel=[\'"](?:image_src|preload)[\"][^>]+href=[\'"]([^\'"]+)[\'"]',
        r'"image"\s*:\s*"(https?:\\/\\/[^"]+|\\/\\/[^"]+)"',
    ]:
        match = re.search(pattern, detail_html, flags=re.IGNORECASE)
        if match:
            return normalize_url(html.unescape(match.group(1).replace("\\/", "/").strip()))

    # 3) Representative product images in body.
    image_patterns = [
        r'<img[^>]+class=[\'"][^\'"]*(?:big_img|prod_img|thumb|photo|swiper-lazy)[^\'"]*[\'"][^>]+(?:src|data-src|data-original|data-lazy)=[\'"]([^\'"]+)[\'"]',
        r'<img[^>]+(?:id|class)=[\'"][^\'"]*(?:product|main|represent)[^\'"]*[\'"][^>]+(?:src|data-src|data-original|data-lazy)=[\'"]([^\'"]+)[\'"]',
        r'<img[^>]+(?:src|data-src|data-original|data-lazy)=[\'"]([^\'"]+)[\'"]',
    ]
    for pattern in image_patterns:
        match = re.search(pattern, detail_html, flags=re.IGNORECASE)
        if match:
            url = match.group(1).strip()
            if url and not url.startswith("data:"):
                return normalize_url(html.unescape(url))
    return None


def parse_tag_attributes(tag_html: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, _, value in re.findall(r'([a-zA-Z_:][\w:.-]*)\s*=\s*([\'"])(.*?)\2', tag_html):
        attrs[key.lower()] = value
    return attrs


def extract_structured_specs(detail_html: str) -> dict[str, str]:
    specs: dict[str, str] = {}
    row_pattern = re.compile(
        r"<(?:tr|li)[^>]*>\s*(?:<th[^>]*>|<dt[^>]*>|<strong[^>]*>)(.*?)</(?:th|dt|strong)>"
        r"\s*(?:<td[^>]*>|<dd[^>]*>|<span[^>]*>)(.*?)</(?:td|dd|span)>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    for key_html, value_html in row_pattern.findall(detail_html):
        key = text_of(key_html).lower()
        value = text_of(value_html)
        if key and value:
            specs[key] = value
    return specs




def extract_mobile_specs(detail_html: str) -> dict[str, str]:
    specs: dict[str, str] = {}

    patterns = [
        re.compile(
            r'<li[^>]*>\s*<span[^>]*class=[\'"][^\'"]*(?:tit|title|name)[^\'"]*[\'"][^>]*>(.*?)</span>\s*<span[^>]*class=[\'"][^\'"]*(?:txt|value|desc)[^\'"]*[\'"][^>]*>(.*?)</span>',
            flags=re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r'<div[^>]*class=[\'"][^\'"]*(?:spec|info)[^\'"]*[\'"][^>]*>\s*<span[^>]*>(.*?)</span>\s*<span[^>]*>(.*?)</span>',
            flags=re.IGNORECASE | re.DOTALL,
        ),
    ]

    for pattern in patterns:
        for key_html, value_html in pattern.findall(detail_html):
            key = text_of(key_html).lower()
            value = text_of(value_html)
            if key and value and key not in specs:
                specs[key] = value
    return specs

def parse_pd_from_structured_specs(specs: dict[str, str]) -> int | None:
    key_priority = [
        "usb-c pd",
        "pd 충전",
        "power delivery",
        "usb-c",
        "type-c",
        "충전",
        "충전 출력",
    ]
    for key in key_priority:
        for spec_key, spec_value in specs.items():
            if key in spec_key:
                watt = parse_usb_c_pd_watt(f"{spec_key} {spec_value}".lower())
                if watt is not None:
                    return watt
    return None


def parse_detail_specs(detail_html: str) -> tuple[int | None, str | None, str | None]:
    specs = extract_structured_specs(detail_html)
    specs.update(extract_mobile_specs(detail_html))
    detail_text = text_of(detail_html).lower()

    # PD parsing priority:
    # 1) Structured specs/table
    # 2) Explicit keyword context
    # 3) Global text fallback
    usb_c_pd_watt = parse_pd_from_structured_specs(specs)
    if usb_c_pd_watt is None:
        keyword_text = " ".join(
            re.findall(
                r"(?:usb[\s\-]?c|type[\s\-]?c|power\s*delivery|pd|충전)[^.]{0,120}",
                detail_text,
                flags=re.IGNORECASE,
            )
        ).lower()
        usb_c_pd_watt = parse_usb_c_pd_watt(keyword_text) if keyword_text else None
    if usb_c_pd_watt is None:
        usb_c_pd_watt = parse_usb_c_pd_watt(detail_text)

    vesa_mount_mm = None
    for spec_key, spec_value in specs.items():
        if "vesa" in spec_key or "베사" in spec_key:
            vesa_mount_mm = parse_vesa_mount(f"{spec_key} {spec_value}".lower())
            if vesa_mount_mm:
                break
    if vesa_mount_mm is None:
        vesa_mount_mm = parse_vesa_mount(detail_text)

    image_url = parse_image_url(detail_html)
    return usb_c_pd_watt, vesa_mount_mm, image_url


def parse_products(html: str) -> list[dict]:
    items = []
    blocks = re.findall(r'(<li[^>]+class="[^"]*prod_item[^"]*"[\s\S]*?</li>)', html)

    for block in blocks[:60]:
        name_match = re.search(r'class="prod_name"[\s\S]*?<a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', block)
        if not name_match:
            continue

        url, name_html = name_match.groups()
        name = text_of(name_html)

        price_match = re.search(r'class="price_sect"[\s\S]*?<strong>([\d,]+)</strong>', block)
        price = parse_price(price_match.group(1)) if price_match else None

        # Product spec text frequently appears in prod_spec_set and ext columns.
        spec_text = text_of(block).lower()

        if "27" not in spec_text:
            continue
        if not any(token in spec_text for token in ["3840x2160", "4k", "uhd"]):
            continue
        if "usb-c" not in spec_text and "type-c" not in spec_text:
            continue

        usb_c_pd_watt = parse_usb_c_pd_watt(spec_text)
        vesa_mount_mm = parse_vesa_mount(spec_text)

        if price is None:
            continue

        items.append(
            {
                "name": name,
                "brand": detect_brand(name),
                "price": price,
                "size_inch": 27,
                "resolution": "3840x2160",
                "usb_c_pd_watt": usb_c_pd_watt,
                "vesa_mount_mm": vesa_mount_mm,
                "url": normalize_url(url),
            }
        )

    dedup = {}
    for item in items:
        dedup[item["name"]] = item

    return sorted(dedup.values(), key=lambda x: x["price"])


def enrich_products_with_detail(products: list[dict]) -> list[dict]:
    detail_cache: dict[str, tuple[int | None, str | None, str | None]] = {}

    for product in products:
        url = product.get("url")
        if not isinstance(url, str) or not url:
            product["image_url"] = None
            continue

        if url not in detail_cache:
            try:
                detail_html = fetch_html(url)
                detail_cache[url] = parse_detail_specs(detail_html)
            except Exception as exc:
                logger.warning("Detail parsing failed name=%s url=%s err=%s", product.get("name"), url, exc)
                detail_cache[url] = (None, None, None)

        detail_pd, detail_vesa, detail_image = detail_cache[url]
        if detail_pd is not None:
            product["usb_c_pd_watt"] = detail_pd
        if detail_vesa is not None:
            product["vesa_mount_mm"] = detail_vesa
        product["image_url"] = detail_image

    return products


def main() -> int:
    configure_logging()
    all_products: list[dict] = []
    for query in QUERIES:
        url = "https://search.danawa.com/dsearch.php?" + urllib.parse.urlencode(
            {"k1": query, "module": "goods", "act": "dispMain"}
        )
        html = fetch_html(url)
        all_products.extend(parse_products(html))

    dedup = {}
    for product in all_products:
        dedup[product["name"]] = product
    products = sorted(dedup.values(), key=lambda x: x["price"])
    products = enrich_products_with_detail(products)

    payload = {
        "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "query": QUERIES[0],
        "queries": QUERIES,
        "source": "danawa",
        "filters_applied": {
            "size_inch": 27,
            "resolution_tokens": ["4k", "uhd", "3840x2160"],
            "required_ports": ["usb-c 또는 type-c"],
            "queries": QUERIES,
        },
        "products": products,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved {len(products)} products to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
