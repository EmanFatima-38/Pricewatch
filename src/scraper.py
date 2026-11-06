import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BOT_NAME = "PriceWatchBot"
HEADERS = {"User-Agent": f"{BOT_NAME}/1.0 (learning project)"}
PAGE_SIZE = 250        # the most products Shopify returns per page
MAX_PAGES = 20         # safety limit: at most 5,000 products per store


class StoreBlocked(Exception):
    """The store asked us to slow down (HTTP 429), so we stop."""


class NotAllowed(Exception):
    """The store's robots.txt says bots may not read this page, so we skip it."""


def allowed_by_robots(url):
    """Check the site's robots.txt before reading a page, like a polite bot should."""
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        response = requests.get(robots_url, headers=HEADERS, timeout=10)
    except requests.RequestException:
        return False                   # can't read the rules, so don't assume permission
    if response.status_code in (401, 403) or response.status_code >= 500:
        return False                   # the site is refusing or broken: stay away
    if response.status_code >= 400:
        return True                    # no robots.txt means no rules
    rules = RobotFileParser()
    rules.parse(response.text.splitlines())
    return rules.can_fetch(BOT_NAME, url)


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


# ---------- Store 2: Shopify stores ----------

def product_handle(url):
    """Get the product's short name from a link like .../products/luna-smart-watch."""
    path = urlparse(url).path.rstrip("/")
    if "/products/" not in path:
        raise ValueError(f"Not a product link: {url}")
    return path.split("/products/")[-1].split("/")[0]


def canonical_url(url):
    """One standard link per product, so the same product is never saved twice."""
    parts = urlparse(url)
    host = parts.netloc.lower().removeprefix("www.")
    return f"https://{host}/products/{product_handle(url)}"


def shopify_data_url(url):
    """Turn a product page link into the store's JSON data link."""
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}/products/{product_handle(url)}.js"


def scrape_shopify(url):
    """Check one product (used for single links in products.txt)."""
    if not allowed_by_robots(shopify_data_url(url)):
        raise NotAllowed(f"robots.txt does not allow bots to read {url}")
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

    # This endpoint gives prices in paisa (x100), so 299000 means Rs. 2,990
    price = variant["price"] / 100
    compare_at = variant.get("compare_at_price")
    original_price = compare_at / 100 if compare_at and compare_at > variant["price"] else None

    return {
        "name": data["title"],
        "price": price,
        "original_price": original_price,
        "in_stock": bool(data.get("available")),
        "url": canonical_url(url),
        "scraped_at": now_utc(),
    }


def product_from_catalog(store, item, scraped_at):
    """Turn one product from a store's catalog into our standard dictionary."""
    variants = item.get("variants") or []
    if not variants:
        return None

    variant = next((v for v in variants if v.get("available")), variants[0])

    # The catalog endpoint gives prices as text in rupees, like "7999.00"
    price = float(variant["price"])
    compare_at = variant.get("compare_at_price")
    compare_at = float(compare_at) if compare_at else None

    return {
        "name": item["title"],
        "price": price,
        "original_price": compare_at if compare_at and compare_at > price else None,
        "in_stock": any(v.get("available") for v in variants),
        "url": canonical_url(f"{store}/products/{item['handle']}"),
        "scraped_at": scraped_at,
    }


def scrape_shopify_store(store_url):
    """Check every product in a Shopify store, a page of up to 250 at a time."""
    store = store_url.rstrip("/")
    if not allowed_by_robots(f"{store}/products.json"):
        raise NotAllowed(f"{store}/robots.txt does not allow bots to read the catalog")
    scraped_at = now_utc()
    products = []

    for page in range(1, MAX_PAGES + 1):
        response = requests.get(
            f"{store}/products.json",
            params={"limit": PAGE_SIZE, "page": page},
            headers=HEADERS,
            timeout=20,
        )
        if response.status_code == 429:
            if not products:
                raise StoreBlocked(f"{store} asked us to slow down (429)")
            print(f"  {store} asked us to slow down on page {page}; keeping what we have.")
            break
        response.raise_for_status()

        items = response.json().get("products", [])
        for item in items:
            product = product_from_catalog(store, item, scraped_at)
            if product:
                products.append(product)

        if len(items) < PAGE_SIZE:
            break                      # that was the last page
        time.sleep(2)                  # be polite between pages

    return products


# ---------- Pick the right scraper for each single link ----------

def scrape_product(url):
    """Download a product page and return its details as a dictionary."""
    if "books.toscrape.com" in url:
        return scrape_books_toscrape(url)
    return scrape_shopify(url)