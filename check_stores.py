"""Check which stores in candidate_stores.txt let PriceWatch read their product catalog."""
import time

import requests

from main import load_lines
from src.scraper import HEADERS

working, blocked, unsupported = [], [], []

for store in load_lines("candidate_stores.txt"):
    store = store.rstrip("/")
    try:
        response = requests.get(f"{store}/products.json", params={"limit": 1},
                                headers=HEADERS, timeout=15)
        if response.status_code == 429:
            blocked.append(store)
            print(f"BLOCKED      {store} (429: asks bots to slow down)")
        elif response.status_code != 200:
            unsupported.append(store)
            print(f"UNSUPPORTED  {store} (HTTP {response.status_code})")
        else:
            products = response.json().get("products", [])
            if not products:
                unsupported.append(store)
                print(f"UNSUPPORTED  {store} (no products returned)")
            else:
                variant = products[0]["variants"][0]
                working.append(store)
                print(f"WORKS        {store}  e.g. {products[0]['title']} | Rs. {variant['price']}")
    except ValueError:
        unsupported.append(store)
        print(f"UNSUPPORTED  {store} (not a Shopify catalog)")
    except Exception as error:
        unsupported.append(store)
        print(f"ERROR        {store} ({error})")
    time.sleep(3)  # one request per store, with a pause

print(f"\n{len(working)} working, {len(blocked)} blocked, {len(unsupported)} unsupported.")
print("\nCopy these lines into stores.txt:")
for store in working:
    print(store)