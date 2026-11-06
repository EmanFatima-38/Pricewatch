"""One-time cleanup: remove the books.toscrape.com practice data from the database."""
from src.database import get_connection, init_db

conn = get_connection()
init_db(conn)

practice = "SELECT id FROM products WHERE url LIKE '%books.toscrape.com%'"
prices = conn.execute(f"DELETE FROM prices WHERE product_id IN ({practice})").rowcount
products = conn.execute("DELETE FROM products WHERE url LIKE '%books.toscrape.com%'").rowcount
conn.commit()
conn.close()

print(f"Removed {products} practice products and {prices} of their price records.")