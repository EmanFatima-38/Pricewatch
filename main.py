import time

from src.database import get_connection, init_db, save_result
from src.scraper import scrape_product


def load_urls(path="products.txt"):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    urls = load_urls()
    print(f"Checking {len(urls)} products...\n")

    conn = get_connection()
    init_db(conn)

    saved = 0
    for url in urls:
        try:
            product = scrape_product(url)
            save_result(conn, product)
            saved += 1
            stock = "In stock" if product["in_stock"] else "Out of stock"
            print(f"Saved: {product['name']}: {product['price']} ({stock})")
        except Exception as error:
            print(f"Failed: {url}\n  Reason: {error}")

        time.sleep(1)  # be polite: wait 1 second between requests

    conn.close()
    print(f"\nDone. Saved {saved} of {len(urls)} products.")


if __name__ == "__main__":
    main()