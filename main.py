import sys
import time
from pathlib import Path

from src.database import get_connection, init_db, save_result
from src.scraper import scrape_product, scrape_shopify_store


def load_lines(path):
    """Read a list file, skipping empty lines and lines starting with #."""
    file = Path(path)
    if not file.exists():
        return []
    lines = [line.strip() for line in file.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line and not line.startswith("#")]


def main():
    stores = load_lines("stores.txt")
    urls = load_lines("products.txt")
    print(f"Checking {len(stores)} store(s) and {len(urls)} single product link(s)...\n")

    conn = get_connection()
    init_db(conn)
    saved = 0

    # 1. Whole stores: every product in each store's catalog
    for store in stores:
        try:
            products = scrape_shopify_store(store)
            changes = sum(save_result(conn, product, commit=False) for product in products)
            conn.commit()
            saved += len(products)
            on_sale = sum(1 for p in products if p["original_price"])
            print(f"Saved: {store}: {len(products)} products checked, "
                  f"{on_sale} on sale, {changes} new or changed prices")
        except Exception as error:
            print(f"Failed: {store}\n  Reason: {error}")
        time.sleep(2)  # be polite between stores

    # 2. Single product links
    for url in urls:
        try:
            product = scrape_product(url)
            save_result(conn, product)
            saved += 1
            print(f"Saved: {product['name']}: {product['price']}")
        except Exception as error:
            print(f"Failed: {url}\n  Reason: {error}")
        time.sleep(1)  # be polite between requests

    conn.close()
    print(f"\nDone. Checked {saved} products.")

    if saved == 0:
        sys.exit(1)  # makes the GitHub Actions run show red, so failures get noticed


if __name__ == "__main__":
    main()