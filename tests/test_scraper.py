import unittest
from unittest import mock

from src import scraper


def fake_response(status=200, json_data=None):
    response = mock.Mock()
    response.status_code = status
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def text_response(status=200, text=""):
    response = mock.Mock()
    response.status_code = status
    response.text = text
    return response


def catalog_item(handle, price, compare_at=None, available=True):
    return {
        "title": handle.replace("-", " ").title(),
        "handle": handle,
        "variants": [{"price": price, "compare_at_price": compare_at, "available": available}],
    }


class UrlTests(unittest.TestCase):
    def test_canonical_url_removes_collection_and_www(self):
        url = "https://www.zerolifestyle.co/collections/sale/products/luna-smart-watch?variant=1"
        self.assertEqual(scraper.canonical_url(url),
                         "https://zerolifestyle.co/products/luna-smart-watch")

    def test_shopify_data_url(self):
        url = "https://zerolifestyle.co/collections/sale/products/luna-smart-watch"
        self.assertEqual(scraper.shopify_data_url(url),
                         "https://zerolifestyle.co/products/luna-smart-watch.js")

    def test_rejects_non_product_links(self):
        with self.assertRaises(ValueError):
            scraper.canonical_url("https://zerolifestyle.co/collections/sale")

    def test_parse_price(self):
        self.assertEqual(scraper.parse_price("Rs. 1,299"), 1299.0)
        self.assertEqual(scraper.parse_price("£51.77"), 51.77)
        self.assertIsNone(scraper.parse_price("no price"))


class RobotsTests(unittest.TestCase):
    def test_allows_when_rules_allow(self):
        rules = "User-agent: *\nDisallow: /checkout\n"
        with mock.patch.object(scraper.requests, "get", return_value=text_response(text=rules)):
            self.assertTrue(scraper.allowed_by_robots("https://shop.pk/products.json"))

    def test_blocks_when_rules_disallow(self):
        rules = "User-agent: *\nDisallow: /products\n"
        with mock.patch.object(scraper.requests, "get", return_value=text_response(text=rules)):
            self.assertFalse(scraper.allowed_by_robots("https://shop.pk/products.json"))

    def test_blocks_when_our_bot_is_named(self):
        rules = "User-agent: PriceWatchBot\nDisallow: /\n"
        with mock.patch.object(scraper.requests, "get", return_value=text_response(text=rules)):
            self.assertFalse(scraper.allowed_by_robots("https://shop.pk/products.json"))

    def test_no_robots_file_means_no_rules(self):
        with mock.patch.object(scraper.requests, "get", return_value=text_response(status=404)):
            self.assertTrue(scraper.allowed_by_robots("https://shop.pk/products.json"))

    def test_store_is_skipped_when_disallowed(self):
        with mock.patch.object(scraper, "allowed_by_robots", return_value=False):
            with self.assertRaises(scraper.NotAllowed):
                scraper.scrape_shopify_store("https://shop.pk")


class StoreCatalogTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(scraper, "allowed_by_robots", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reads_prices_and_sale(self):
        page = {"products": [
            catalog_item("gravity-earbuds", "2999.00", "4999.00"),
            catalog_item("power-bank", "5999.00", None),
        ]}
        with mock.patch.object(scraper.requests, "get", return_value=fake_response(json_data=page)):
            products = scraper.scrape_shopify_store("https://zerolifestyle.co/")

        self.assertEqual(len(products), 2)
        earbuds = products[0]
        self.assertEqual(earbuds["price"], 2999.0)
        self.assertEqual(earbuds["original_price"], 4999.0)
        self.assertEqual(earbuds["url"], "https://zerolifestyle.co/products/gravity-earbuds")
        self.assertIsNone(products[1]["original_price"])

    def test_original_price_ignored_when_not_higher(self):
        page = {"products": [catalog_item("watch", "4999.00", "4999.00")]}
        with mock.patch.object(scraper.requests, "get", return_value=fake_response(json_data=page)):
            products = scraper.scrape_shopify_store("https://zerolifestyle.co")
        self.assertIsNone(products[0]["original_price"])

    def test_reads_every_page(self):
        full_page = {"products": [catalog_item(f"item-{i}", "100") for i in range(scraper.PAGE_SIZE)]}
        last_page = {"products": [catalog_item("last-item", "100")]}
        responses = [fake_response(json_data=full_page), fake_response(json_data=last_page)]
        with mock.patch.object(scraper.requests, "get", side_effect=responses), \
             mock.patch.object(scraper.time, "sleep"):
            products = scraper.scrape_shopify_store("https://zerolifestyle.co")
        self.assertEqual(len(products), scraper.PAGE_SIZE + 1)

    def test_stops_when_store_blocks_us(self):
        with mock.patch.object(scraper.requests, "get", return_value=fake_response(status=429)):
            with self.assertRaises(scraper.StoreBlocked):
                scraper.scrape_shopify_store("https://zerolifestyle.co")


if __name__ == "__main__":
    unittest.main()