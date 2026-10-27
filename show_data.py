from src.database import get_connection

conn = get_connection()

rows = conn.execute("""
    SELECT products.name, prices.price, prices.in_stock, prices.scraped_at
    FROM prices
    JOIN products ON products.id = prices.product_id
    ORDER BY products.name, prices.scraped_at
""").fetchall()

for name, price, in_stock, scraped_at in rows:
    stock = "In stock" if in_stock else "Out of stock"
    print(f"{scraped_at} | {name}: {price} ({stock})")

print(f"\nTotal price records: {len(rows)}")
conn.close()