import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from src.analysis import check_discount
from src.scraper import canonical_url

DB_PATH = Path("data/prices.db")

st.set_page_config(page_title="PriceWatch", page_icon="📈", layout="wide")


@st.cache_data(ttl=600)
def load_data():
    """Read the full price history from the database."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT products.name, products.url, products.last_seen,
               prices.price, prices.original_price, prices.in_stock, prices.scraped_at
        FROM prices
        JOIN products ON products.id = prices.product_id
        ORDER BY prices.scraped_at
        """,
        conn,
    )
    conn.close()
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
    df["date"] = df["scraped_at"].dt.tz_convert("Asia/Karachi").dt.date
    last_seen = pd.to_datetime(df["last_seen"].fillna(df["scraped_at"].astype(str)), utc=True)
    df["last_seen_date"] = last_seen.dt.tz_convert("Asia/Karachi").dt.date
    df["store"] = df["url"].map(lambda u: urlparse(u).netloc.removeprefix("www."))
    return df


def daily_pairs(group):
    """
    One (price, original_price) pair per day, oldest first.

    Prices are only saved when they change, so days without a new row
    keep the previous day's price, up to the day the product was last seen.
    """
    days = (
        group.sort_values("scraped_at")
        .drop_duplicates("date", keep="last")
        .set_index("date")[["price", "original_price", "in_stock"]]
    )
    first_day, last_day = days.index.min(), max(days.index.max(), group["last_seen_date"].max())
    every_day = pd.date_range(first_day, last_day, freq="D").date
    days = days.reindex(every_day, method="ffill")   # fills only the missing days
    return days, [
        (row.price, None if pd.isna(row.original_price) else row.original_price)
        for row in days.itertuples()
    ]


@st.cache_data(ttl=600)
def summarize(df):
    """The verdict for every product, for the overview table."""
    rows = []
    for url, group in df.groupby("url"):
        days, pairs = daily_pairs(group)
        result = check_discount(pairs)
        rows.append({
            "Product": group["name"].iloc[-1],
            "Store": group["store"].iloc[-1],
            "Current price": days["price"].iloc[-1],
            "Store claims": f"{result['claimed_off']}% off" if "claimed_off" in result else "",
            "Days tracked": len(days),
            "Verdict": result["verdict"],
            "url": url,
        })
    return pd.DataFrame(rows)


st.title("📈 PriceWatch")
st.caption("Tracks product prices every day to show whether a discount is real.")
st.caption(
    "ℹ️ Verdicts are automatic estimates based only on prices PriceWatch has recorded. "
    "They can be incomplete or wrong, and are not a statement about any store's intentions."
)

if not DB_PATH.exists():
    st.error("No data yet. Run `python main.py` first.")
    st.stop()

df = load_data()
summary = summarize(df)
stores = sorted(df["store"].unique())

st.caption(
    "Supported stores: " + ", ".join(
        f"{s} ({(summary['Store'] == s).sum()} products)" for s in stores
    )
)

# ---------- Find a product ----------
st.subheader("🔍 Find a product")
col_search, col_store = st.columns([3, 1])
query = col_search.text_input("Search by name, or paste a product link").strip()
store_choice = col_store.selectbox("Store", ["All stores"] + stores)

matches = summary if store_choice == "All stores" else summary[summary["Store"] == store_choice]

if query.lower().startswith("http"):
    try:
        wanted = canonical_url(query)
    except ValueError:
        st.warning("That doesn't look like a product link. It should contain /products/.")
        st.stop()
    matches = matches[matches["url"] == wanted]
    if matches.empty:
        store = urlparse(wanted).netloc
        if store in stores:
            st.info("This product isn't in our data yet. New products are picked up "
                    "at the next daily check, so try again tomorrow.")
        else:
            st.info(f"**{store}** isn't a supported store yet. "
                    f"Supported stores: {', '.join(stores)}.")
        st.stop()
elif query:
    matches = matches[matches["Product"].str.contains(query, case=False, regex=False)]

if matches.empty:
    st.info("No products match your search.")
    st.stop()

labels = dict(zip(matches["url"], matches["Product"] + "  ·  " + matches["Store"]))
chosen_url = st.selectbox(
    f"{len(matches)} matching product(s)",
    sorted(labels, key=labels.get),
    format_func=labels.get,
)

history = df[df["url"] == chosen_url]
latest = history.iloc[-1]
daily, pairs = daily_pairs(history)
today = daily.iloc[-1]

# ---------- Key numbers ----------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Current price", f"{today['price']:,.0f}")
col2.metric("Lowest price", f"{daily['price'].min():,.0f}")
col3.metric("Highest price", f"{daily['price'].max():,.0f}")
col4.metric("Average price", f"{daily['price'].mean():,.0f}")

# ---------- Fake discount check ----------
result = check_discount(pairs)

st.subheader("🕵️ Is this discount real?")
verdict = result["verdict"]
if verdict == "Genuine discount":
    st.success(f"✅ **{verdict}**")
elif verdict == "Suspicious discount":
    st.error(f"🚩 **{verdict}**")
elif verdict == "Real drop, exaggerated claim":
    st.warning(f"⚠️ **{verdict}**")
else:
    st.info(f"ℹ️ **{verdict}**")

if "claimed_off" in result:
    c1, c2 = st.columns(2)
    c1.metric("Discount the store claims", f"{result['claimed_off']}%")
    c2.metric("Real discount vs usual price", f"{result['real_off']}%")

for reason in result["reasons"]:
    st.write(f"- {reason}")

stock = "✅ In stock" if today["in_stock"] else "❌ Out of stock"
days = len(daily)
st.write(f"{stock} · Tracked for **{days} day(s)** · [Open product page]({latest['url']})")

# ---------- Price history chart (one point per day) ----------
st.subheader("Price history")
chart = daily[["price", "original_price"]].rename(
    columns={"price": "Price", "original_price": "Store's 'original' price"}
)
st.line_chart(chart.dropna(axis=1, how="all"))

if days < 7:
    st.caption("The chart becomes more useful as more days of data are collected.")

# ---------- All products at a glance ----------
st.subheader("All products")
only_flagged = st.checkbox("Show only suspicious discounts")
table = summary if store_choice == "All stores" else summary[summary["Store"] == store_choice]
if only_flagged:
    table = table[table["Verdict"] == "Suspicious discount"]
st.dataframe(table.drop(columns="url"), hide_index=True)

# ---------- Raw data ----------
with st.expander("See every recorded price change for this product"):
    st.dataframe(
        history[["scraped_at", "price", "original_price", "in_stock"]].sort_values(
            "scraped_at", ascending=False
        )
    )