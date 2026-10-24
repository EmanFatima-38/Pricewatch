import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "PriceWatchBot/1.0 (learning project)"}


def parse_price(text):
    """Turn text like '£51.77' or 'Rs. 1,299' into a number."""
    match = re.search(r"[\d,]+\.?\d*", text)
    if not match:
        return None
    return float(match.group().replace(",", ""))


def scrape_product(url):
    """Download a product page and return its details as a dictionary."""
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()  # stop if the page returned an error like 404
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")

    name_tag = soup.select_one("div.product_main h1")
    price_tag = soup.select_one("p.price_color")
    stock_tag = soup.select_one("p.availability")

    if not name_tag or not price_tag:
        raise ValueError(f"Could not find product details on {url}")

    return {
        "name": name_tag.get_text(strip=True),
        "price": parse_price(price_tag.get_text()),
        "in_stock": ("In stock" in stock_tag.get_text()) if stock_tag else None,
        "url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }