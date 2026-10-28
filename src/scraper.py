import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "PriceWatchBot/1.0 (learning project)"}


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_price(text):
    """Turn text like '£51.77' or 'Rs. 1,299' into a number."""
    match = re.search(r"[\d,]+\.?\d*", text)
    if not match:
        return None
    return float(match.group().replace(",", ""))


# ---------- Store 1: books.toscrape.com (practice site, reads HTML) ----------

def scrape_books_toscrape(url):
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
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
        "original_price": None,  # this site never shows a crossed-out price
        "in_stock": ("In stock" in stock_tag.get_text()) if stock_tag else None,
        "url": url,
        "scraped_at": now_utc(),
    }


# ---------- Store 2: Shopify stores (reads the store's JSON data) ----------

def shopify_data_url(url):
    """Turn a product page link into the store's JSON data link."""
    parts = urlparse(url)
    path = parts.path.rstrip("/")
    if "/products/" not in path:
        raise ValueError(f"Not a product link: {url}")
    handle = path.split("/products/")[-1].split("/")[0]
    return f"{parts.scheme}://{parts.netloc}/products/{handle}.js"


def scrape_shopify(url):
    response = requests.get(shopify_data_url(url), headers=HEADERS, timeout=10)
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        raise ValueError(f"This store is not supported (no product data found): {url}")

    variants = data.get("variants") or []
    if not variants:
        raise ValueError(f"No price information found on {url}")

    # Use the first variant that is in stock, otherwise the first variant
    variant = next((v for v in variants if v.get("available")), variants[0])

    # Shopify gives prices in paisa (x100), so 299000 means Rs. 2,990
    price = variant["price"] / 100
    compare_at = variant.get("compare_at_price")
    original_price = compare_at / 100 if compare_at and compare_at > variant["price"] else None

    return {
        "name": data["title"],
        "price": price,
        "original_price": original_price,
        "in_stock": bool(data.get("available")),
        "url": url,
        "scraped_at": now_utc(),
    }


# ---------- Pick the right scraper for each link ----------

def scrape_product(url):
    """Download a product page and return its details as a dictionary."""
    if "books.toscrape.com" in url:
        return scrape_books_toscrape(url)
    return scrape_shopify(url)