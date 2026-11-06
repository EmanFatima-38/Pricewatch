import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.database import get_connection, init_db, save_result


def product(price, scraped_at, original=None):
    return {"name": "Luna Smartwatch", "url": "https://zerolifestyle.co/products/luna",
            "price": price, "original_price": original, "in_stock": True,
            "scraped_at": scraped_at}


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.conn = get_connection(Path(self.folder.name) / "test.db")
        init_db(self.conn)

    def tearDown(self):
        self.conn.close()
        self.folder.cleanup()

    def test_unchanged_price_is_not_saved_again(self):
        self.assertTrue(save_result(self.conn, product(4999, "2026-11-01T03:00:00+00:00", 9999)))
        self.assertFalse(save_result(self.conn, product(4999, "2026-11-02T03:00:00+00:00", 9999)))

        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0], 1)
        last_seen = self.conn.execute("SELECT last_seen FROM products").fetchone()[0]
        self.assertEqual(last_seen, "2026-11-02T03:00:00+00:00")

    def test_sale_ending_is_saved(self):
        save_result(self.conn, product(4999, "2026-11-01T03:00:00+00:00", 9999))
        self.assertTrue(save_result(self.conn, product(4999, "2026-11-02T03:00:00+00:00", None)))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0], 2)

    def test_history_grows_but_product_is_stored_once(self):
        save_result(self.conn, product(4999, "2026-11-01T03:00:00+00:00", 9999))
        save_result(self.conn, product(4499, "2026-11-02T03:00:00+00:00", 9999))

        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0], 1)
        prices = self.conn.execute("SELECT price, original_price FROM prices").fetchall()
        self.assertEqual(prices, [(4999.0, 9999.0), (4499.0, 9999.0)])

    def test_upgrades_an_old_database(self):
        path = Path(self.folder.name) / "old.db"
        old = sqlite3.connect(path)
        old.executescript("""
            CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   url TEXT UNIQUE NOT NULL, name TEXT NOT NULL);
            CREATE TABLE prices (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 product_id INTEGER NOT NULL REFERENCES products(id),
                                 price REAL, in_stock INTEGER, scraped_at TEXT NOT NULL);
        """)
        old.close()

        conn = get_connection(path)
        init_db(conn)
        init_db(conn)  # running it twice must be safe
        columns = [row[1] for row in conn.execute("PRAGMA table_info(prices)")]
        product_columns = [row[1] for row in conn.execute("PRAGMA table_info(products)")]
        conn.close()
        self.assertIn("original_price", columns)
        self.assertIn("last_seen", product_columns)


if __name__ == "__main__":
    unittest.main()