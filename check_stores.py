import time

import requests

HEADERS = {"User-Agent": "PriceWatchBot/1.0 (learning project)"}

STORES = [
    "https://www.beechtree.pk",
    "https://www.mistore.pk",
    "https://bonanzasatrangi.com",
    "https://www.asimjofa.com",
    "https://www.bagallery.com",
    "https://zerolifestyle.co",
    "https://pk.sapphireonline.pk",
]

for store in STORES:
    try:
        response = requests.get(
            f"{store}/products.json?limit=1", headers=HEADERS, timeout=10
        )
        if response.status_code != 200:
            print(f"❌ {store} -> blocked or not available ({response.status_code})")
        else:
            product = response.json()["products"][0]
            variant = product["variants"][0]
            print(f"✅ {store} -> works!")
            print(f"   Example: {product['title']} | price: {variant['price']} | "
                  f"original: {variant.get('compare_at_price')}")
            print(f"   Link: {store}/products/{product['handle']}")
    except Exception as error:
        print(f"❌ {store} -> error: {error}")

    time.sleep(2)  # be polite between stores