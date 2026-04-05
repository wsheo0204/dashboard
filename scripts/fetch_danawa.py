#!/usr/bin/env python3
"""Fetch Danawa monitor list and save filtered products to data/products.json.

This script is designed for GitHub Actions.
"""

from __future__ import annotations

import datetime as dt
import json
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


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


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
    patterns = [
        r"(?:pd|power\s*delivery)\D{0,12}(\d{2,3})\s*w",
        r"usb[\s\-]?c\D{0,12}(\d{2,3})\s*w",
        r"type[\s\-]?c\D{0,12}(\d{2,3})\s*w",
    ]
    for pattern in patterns:
        match = re.search(pattern, spec_text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def parse_vesa_mount(spec_text: str) -> str | None:
    match = re.search(r"(?:vesa|베사)\D{0,10}(\d{2,3})\D{0,4}x\D{0,4}(\d{2,3})", spec_text)
    if not match:
        return None
    return f"{match.group(1)}x{match.group(2)}"


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
                "url": url,
            }
        )

    dedup = {}
    for item in items:
        dedup[item["name"]] = item

    return sorted(dedup.values(), key=lambda x: x["price"])


def main() -> int:
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
