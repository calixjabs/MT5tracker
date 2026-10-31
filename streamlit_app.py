import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from datetime import datetime, timedelta

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
        page_title="EA Portfolio Dashboard",
            page_icon="📈",
                layout="wide",
                    initial_sidebar_state="expanded"
)

# -----------------------------
# SUPABASE CONNECTION
# -----------------------------
@st.cache_resource
def init_supabase():
        url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
                return create_client(url, key)

                supabase: Client = init_supabase()

                # -----------------------------
                # LOAD DATA
                # -----------------------------
                @st.cache_data(ttl=60)  # refresh every 60 seconds
                def load_trades():
                        response = supabase.table("trades").select("*").order("close_time", desc=True).execute()
                            df = pd.DataFrame(response.data)
                                
                                    if df.empty:
                                                return df
                                                    
                                                        # Convert types
                                                            df["close_time"] = pd.to_datetime(df["close_time"])
                                                                df["open_time"] = pd.to_datetime(df["open_time"])
                                                                    df["profit"] = pd.to_numeric(df["profit"])
                                                                        df["volume"] = pd.to_numeric(df["volume"])
                                                                            df["magic"] = df["magic"].astype(str)  # easier for filtering
                                                                                
                                                                                    return df

                                                                                    df = load_trades()

                                                                                    # -----------------------------
                                                                                    # SIDEBAR FILTERS
                                                                                    # -----------------------------
                                                                                    st.sidebar.title("Filters")

                                                                                    if df.empty:
                                                                                            st.warning("No trades found in Supabase yet.")
                                                                                                st.stop()

                                                                                                # Magic Number filter
                                                                                                all_magics = sorted(df["magic"].unique().tolist())
                                                                                                selected_magics = st.sidebar.multiselect(
                                                                                                        "Magic Numbers (EAs)",
                                                                                                            options=all_magics,
                                                                                                                default=all_magics
                                                                                                )

                                                                                                # Date filter
                                                                                                min_date = df["close_time"].min().date()
                                                                                                max_date = df["close_time"].max().date()

                                                                                                date_range = st.sidebar.date_input(
                                                                                                        "Date Range",
                                                                                                            value=(min_date, max_date),
                                                                                                                min_value=min_date,
                                                                                                                    max_value=max_date
                                                                                                )

                                                                                                # Apply filters
                                                                                                mask = df["magic"].isin(selected_magics)
                                                                                                if len(date_range) == 2:
                                                                                                        mask &= (df["close_time"].dt.date >= date_range[0]) & (df["close_time"].dt.date <= date_range[1])

                                                                                                        filtered = df[mask].copy()

                                                                                                        # -----------------------------
                                                                                                        # HEADER
                                                                                                        # -----------------------------
                                                                                                        st.title("EA Portfolio Dashboard")
                                                                                                        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                                                                                                        # -----------------------------
                                                                                                        # KPI CARDS
                                                                                                        # -----------------------------
                                                                                                        total_profit = filtered["profit"].sum()
                                                                                                        total_trades = len(filtered)
                                                                                                        win_trades = len(filtered[filtered["profit"] > 0])
                                                                                                        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
                                                                                                        profit_factor = (
                                                                                                                filtered[filtered["profit"] > 0]["profit"].sum() /
                                                                                                                    abs(filtered[filtered["profit"] < 0]["profit"].sum())
                                                                                                        ) if filtered[filtered["profit"] < 0]["profit"].sum() != 0 else float("inf")

                                                                                                        col1, col2, col3, col4 = st.columns(4)
                                                                                                        col1.metric("Net Profit", f"${total_profit:,.2f}")
                                                                                                        col2.metric("Total Trades", f"{total_trades}")
                                                                                                        col3.metric("Win Rate", f"{win_rate:.1f}%")
                                                                                                        col4.metric("Profit Factor", f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞")

                                                                                                        st.divider()

                                                                                                        # -----------------------------
                                                                                                        # PERFORMANCE BY MAGIC NUMBER
                                                                                                        # -----------------------------
                                                                                                        st.subheader("Performance by EA (Magic Number)")

                                                                                                        magic_stats = (
                                                                                                                filtered.groupby("magic")
                                                                                                                    .agg(
                                                                                                                                trades=("profit", "count"),
                                                                                                                                        net_profit=("profit", "sum"),
                                                                                                                                                win_rate=("profit", lambda x: (x > 0).mean() * 100),
                                                                                                                                                        avg_profit=("profit", "mean")
                                                                                                                    )
                                                                                                                        .reset_index()
                                                                                                                            .sort_values("net_profit", ascending=False)
                                                                                                        )

                                                                                                        st.dataframe(
                                                                                                                magic_stats.style.format({
                                                                                                                            "net_profit": "${:.2f}",
                                                                                                                                    "win_rate": "{:.1f}%",
                                                                                                                                            "avg_profit": "${:.2f}"
                                                                                                                }),
                                                                                                                    use_container_width=True
                                                                                                        )

                                                                                                        # -----------------------------
                                                                                                        # EQUITY CURVE
                                                                                                        # -----------------------------
                                                                                                        st.subheader("Equity Curve")

                                                                                                        if not filtered.empty:
                                                                                                                equity = filtered.sort_values("close_time").copy()
                                                                                                                    equity["cumulative"] = equity["profit"].cumsum()
                                                                                                                        
                                                                                                                            fig = px.line(
                                                                                                                                        equity,
                                                                                                                                                x="close_time",
                                                                                                                                                        y="cumulative",
                                                                                                                                                                title="Portfolio Equity Curve",
                                                                                                                                                                        labels={"close_time": "Date", "cumulative": "Cumulative Profit ($)"}
                                                                                                                            )
                                                                                                                                fig.update_layout(height=400)
                                                                                                                                    st.plotly_chart(fig, use_container_width=True)

                                                                                                                                    # -----------------------------
                                                                                                                                    # PROFIT BY MAGIC (BAR)
                                                                                                                                    # -----------------------------
                                                                                                                                    st.subheader("Net Profit by Magic Number")

                                                                                                                                    fig2 = px.bar(
                                                                                                                                            magic_stats,
                                                                                                                                                x="magic",
                                                                                                                                                    y="net_profit",
                                                                                                                                                        color="net_profit",
                                                                                                                                                            color_continuous_scale=["#ef4444", "#22c55e"],
                                                                                                                                                                labels={"magic": "Magic Number", "net_profit": "Net Profit ($)"}
                                                                                                                                    )
                                                                                                                                    st.plotly_chart(fig2, use_container_width=True)

                                                                                                                                    # -----------------------------
                                                                                                                                    # RECENT TRADES TABLE
                                                                                                                                    # -----------------------------
                                                                                                                                    st.subheader("Recent Trades")

                                                                                                                                    display_cols = ["close_time", "magic", "symbol", "direction", "volume", "profit", "comment"]
                                                                                                                                    st.dataframe(
                                                                                                                                            filtered[display_cols].head(100).style.format({
                                                                                                                                                        "profit": "${:.2f}",
                                                                                                                                                                "volume": "{:.2f}"
                                                                                                                                            }),
                                                                                                                                                use_container_width=True
                                                                                                                                    )
                                                                                                                }
                                                                                                                    )
)