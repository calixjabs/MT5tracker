import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

st.set_page_config(
    page_title="EA Portfolio Dashboard",
    page_icon="📈",
    layout="wide"
)

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

@st.cache_data(ttl=60)
def load_data():
    response = supabase.table("trades").select("*").order("close_time", desc=True).execute()
    df = pd.DataFrame(response.data)

    if not df.empty:
        df["close_time"] = pd.to_datetime(df["close_time"])
        df["open_time"] = pd.to_datetime(df["open_time"])
        df["profit"] = pd.to_numeric(df["profit"])
        df["magic"] = df["magic"].astype(str)
    return df

df = load_data()

st.sidebar.title("Filters")

if df.empty:
    st.warning("No trades found yet.")
    st.stop()

magics = sorted(df["magic"].unique())
selected_magics = st.sidebar.multiselect("Magic Numbers", magics, default=magics)

min_date = df["close_time"].min().date()
max_date = df["close_time"].max().date()
date_range = st.sidebar.date_input("Date Range", (min_date, max_date))

mask = df["magic"].isin(selected_magics)
if len(date_range) == 2:
    mask = mask & (df["close_time"].dt.date >= date_range[0]) & (df["close_time"].dt.date <= date_range[1])

filtered = df[mask]

st.title("EA Portfolio Dashboard")
st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

total_profit = filtered["profit"].sum()
total_trades = len(filtered)
win_rate = (filtered["profit"] > 0).mean() * 100 if total_trades > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Net Profit", f"${total_profit:,.2f}")
col2.metric("Total Trades", total_trades)
col3.metric("Win Rate", f"{win_rate:.1f}%")

st.divider()

st.subheader("Performance by Magic Number")
magic_summary = (
    filtered.groupby("magic")
    .agg(
        Trades=("profit", "count"),
        Net_Profit=("profit", "sum"),
        Win_Rate=("profit", lambda x: (x > 0).mean() * 100)
    )
    .reset_index()
    .sort_values("Net_Profit", ascending=False)
)

st.dataframe(
    magic_summary.style.format({
        "Net_Profit": "${:.2f}",
        "Win_Rate": "{:.1f}%"
    }),
    use_container_width=True
)

st.subheader("Equity Curve")
if not filtered.empty:
    equity = filtered.sort_values("close_time").copy()
    equity["Cumulative"] = equity["profit"].cumsum()
    fig = px.line(equity, x="close_time", y="Cumulative", title="Portfolio Equity")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Recent Trades")
st.dataframe(
    filtered[["close_time", "magic", "symbol", "direction", "volume", "profit", "comment"]].head(50),
    use_container_width=True
)
