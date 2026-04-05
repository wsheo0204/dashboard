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

QUERY = "27인치 4k usb-c 모니터"
URL = (
    "https://search.danawa.com/dsearch.php?"
    + urllib.parse.urlencode({"k1": QUERY, "module": "goods", "act": "dispMain"})
)
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

        pd_match = re.search(r"(\d{2,3})\s*w", spec_text)
        usb_c_pd_watt = int(pd_match.group(1)) if pd_match else None

        if price is None:
            continue

        items.append(
            {
                "name": name,
                "price": price,
                "size_inch": 27,
                "resolution": "3840x2160",
                "usb_c_pd_watt": usb_c_pd_watt,
                "url": url,
            }
        )

    dedup = {}
    for item in items:
        dedup[item["name"]] = item

    return sorted(dedup.values(), key=lambda x: x["price"])


def main() -> int:
    html = fetch_html(URL)
    products = parse_products(html)

    payload = {
        "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "query": QUERY,
        "source": "danawa",
        "products": products,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved {len(products)} products to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
