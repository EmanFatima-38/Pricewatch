import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path("data/prices.db")

st.set_page_config(page_title="PriceWatch", page_icon="📈", layout="wide")


@st.cache_data(ttl=600)
def load_data():
    """Read the full price history from the database."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT products.name, products.url, prices.price, prices.original_price,
               prices.in_stock, prices.scraped_at
        FROM prices
        JOIN products ON products.id = prices.product_id
        ORDER BY prices.scraped_at
        """,
        conn,
    )
    conn.close()
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
    df["date"] = df["scraped_at"].dt.tz_convert("Asia/Karachi").dt.date
    return df


st.title("📈 PriceWatch")
st.caption("Tracks product prices every day to show whether a discount is real.")

if not DB_PATH.exists():
    st.error("No data yet. Run `python main.py` first.")
    st.stop()

df = load_data()

# ---------- Choose a product ----------
product_name = st.selectbox("Choose a product", sorted(df["name"].unique()))
history = df[df["name"] == product_name]
latest = history.iloc[-1]

# ---------- Key numbers ----------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Current price", f"{latest['price']:,.0f}")
col2.metric("Lowest price", f"{history['price'].min():,.0f}")
col3.metric("Highest price", f"{history['price'].max():,.0f}")
col4.metric("Average price", f"{history['price'].mean():,.0f}")

# ---------- Store's claimed discount ----------
if pd.notna(latest["original_price"]) and latest["original_price"] > latest["price"]:
    off = round((1 - latest["price"] / latest["original_price"]) * 100)
    st.info(
        f"The store shows this as **{off}% off** "
        f"(was {latest['original_price']:,.0f}, now {latest['price']:,.0f})."
    )

stock = "✅ In stock" if latest["in_stock"] else "❌ Out of stock"
days = history["date"].nunique()
st.write(f"{stock} · Tracked for **{days} day(s)** · [Open product page]({latest['url']})")

# ---------- Price history chart (one point per day) ----------
st.subheader("Price history")
daily = history.groupby("date")[["price", "original_price"]].last()
daily = daily.rename(columns={"price": "Price", "original_price": "Store's 'original' price"})
st.line_chart(daily.dropna(axis=1, how="all"))

if days < 7:
    st.caption("The chart becomes more useful as more days of data are collected.")

# ---------- Raw data ----------
with st.expander("See all price checks"):
    st.dataframe(
        history[["scraped_at", "price", "original_price", "in_stock"]].sort_values(
            "scraped_at", ascending=False
        )
    )streamlit run app.py