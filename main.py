import time

from src.scraper import scrape_product


def load_urls(path="products.txt"):
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    urls = load_urls()
    print(f"Checking {len(urls)} products...\n")

    for url in urls:
        try:
            product = scrape_product(url)
            stock = "In stock" if product["in_stock"] else "Out of stock"
            print(f"{product['name']}: {product['price']} ({stock})")
        except Exception as error:
            print(f"Failed: {url}\n  Reason: {error}")

        time.sleep(1)  # be polite: wait 1 second between requests


if __name__ == "__main__":
    main()