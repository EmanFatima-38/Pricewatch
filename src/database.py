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
    """Create the tables if they don't exist yet."""
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
    conn.commit()


def save_result(conn, product):
    """Save one scraped product and its current price."""
    conn.execute(
        """
        INSERT INTO products (url, name) VALUES (?, ?)
        ON CONFLICT(url) DO UPDATE SET name = excluded.name
        """,
        (product["url"], product["name"]),
    )

    product_id = conn.execute(
        "SELECT id FROM products WHERE url = ?", (product["url"],)
    ).fetchone()[0]

    in_stock = None if product["in_stock"] is None else int(product["in_stock"])

    conn.execute(
        "INSERT INTO prices (product_id, price, in_stock, scraped_at) VALUES (?, ?, ?, ?)",
        (product_id, product["price"], in_stock, product["scraped_at"]),
    )
    conn.commit()