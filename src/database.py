import sqlite3
from pathlib import Path

DB_PATH = Path("data/prices.db")


def get_connection(db_path=DB_PATH):
    """Open the database, creating the data folder if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    """Create the tables if they don't exist yet, and add any new columns."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            url  TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prices (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id),
            price      REAL,
            in_stock   INTEGER,
            scraped_at TEXT NOT NULL
        );
    """)

    # Day 3: older databases don't have original_price yet, so add it
    columns = [row[1] for row in conn.execute("PRAGMA table_info(prices)")]
    if "original_price" not in columns:
        conn.execute("ALTER TABLE prices ADD COLUMN original_price REAL")

    # Day 7: remember when each product was last checked
    product_columns = [row[1] for row in conn.execute("PRAGMA table_info(products)")]
    if "last_seen" not in product_columns:
        conn.execute("ALTER TABLE products ADD COLUMN last_seen TEXT")
        conn.execute("""
            UPDATE products SET last_seen =
                (SELECT MAX(scraped_at) FROM prices WHERE prices.product_id = products.id)
        """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_prices_product ON prices(product_id, scraped_at)")
    conn.commit()


def save_result(conn, product, commit=True):
    """
    Save one scraped product.

    A new price row is added only when the price, original price or stock status
    changed since the last check. Otherwise we just record that the product was
    seen again. This keeps the database small even with thousands of products.
    Returns True if a new price row was added.
    """
    conn.execute(
        """
        INSERT INTO products (url, name, last_seen) VALUES (?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET name = excluded.name, last_seen = excluded.last_seen
        """,
        (product["url"], product["name"], product["scraped_at"]),
    )

    product_id = conn.execute(
        "SELECT id FROM products WHERE url = ?", (product["url"],)
    ).fetchone()[0]

    in_stock = None if product["in_stock"] is None else int(product["in_stock"])
    new_values = (product["price"], product["original_price"], in_stock)

    last = conn.execute(
        """
        SELECT price, original_price, in_stock FROM prices
        WHERE product_id = ? ORDER BY scraped_at DESC, id DESC LIMIT 1
        """,
        (product_id,),
    ).fetchone()

    changed = last != new_values
    if changed:
        conn.execute(
            """
            INSERT INTO prices (product_id, price, original_price, in_stock, scraped_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (product_id, *new_values, product["scraped_at"]),
        )
    if commit:
        conn.commit()
    return changed