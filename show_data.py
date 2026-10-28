from src.database import get_connection, init_db

conn = get_connection()
init_db(conn)

rows = conn.execute("""
    SELECT products.name, prices.price, prices.original_price,
           prices.in_stock, prices.scraped_at
    FROM prices
    JOIN products ON products.id = prices.product_id
    ORDER BY products.name, prices.scraped_at
""").fetchall()

for name, price, original_price, in_stock, scraped_at in rows:
    stock = "In stock" if in_stock else "Out of stock"
    if original_price:
        off = round((1 - price / original_price) * 100)
        sale = f" (was {original_price}, {off}% off)"
    else:
        sale = ""
    print(f"{scraped_at} | {name}: {price}{sale} ({stock})")

print(f"\nTotal price records: {len(rows)}")
conn.close()