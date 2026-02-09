import json
import os
import sqlite3
import time

from dotenv import load_dotenv, set_key
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

load_dotenv()

st.set_page_config(page_title="ARCOS War Room", layout="wide", page_icon="⚔️")
DB_FILE = os.environ.get("ARCOS_DB_PATH", "/app/workspace/arcos_vault.db")
WORKSPACE_ROOT = os.environ.get("ARCOS_WORKSPACE", "/app/workspace")

SETTINGS_KEYS = [
    "ARCOS_MIN_WIN_RATE",
    "ARCOS_MIN_SAMPLE_SIZE",
    "ARCOS_EXECUTION_MODE",
]

# --- Auto Refresh (5s) ---
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 5:
    st.session_state.last_refresh = time.time()
    st.rerun()


def clean_rationale(text):
    if not isinstance(text, str):
        return ""
    return text.split("|")[0].strip()


def get_data():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_FILE, timeout=10)
    df = pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 200", conn)
    conn.close()
    return df


def load_portfolio_state():
    portfolio_path = os.path.join(WORKSPACE_ROOT, "portfolio_state.json")
    if not os.path.exists(portfolio_path):
        return None
    with open(portfolio_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_asset_label(asset_name, ticker):
    if asset_name and ticker:
        return f"{asset_name} ({ticker})"
    return asset_name or ticker or "Unknown"


def compute_position_value(position):
    if "current_value" in position:
        return position.get("current_value", 0.0)
    price = position.get("current_price") or position.get("price") or 0.0
    size = position.get("size") or position.get("quantity") or 0.0
    return price * size


def env_value(key):
    return os.environ.get(key, "")


df = get_data()

st.title("🦅 ARCOS: Sovereign Intelligence")

briefing_tab, portfolio_tab, systems_tab = st.tabs(["📡 Briefing", "💼 Portfolio", "⚙️ Systems"])

with briefing_tab:
    st.subheader("🦅 ARCOS Intelligence Briefing")
    if df.empty:
        st.warning("Waiting for Neural Uplink...")
    else:
        last_sig = df.iloc[0]
        last_state = "running"
        if "BUY" in last_sig["signal"]:
            last_state = "complete"
        elif "SELL" in last_sig["signal"]:
            last_state = "error"

        asset_label = format_asset_label(last_sig.get("asset_name"), last_sig.get("ticker"))
        with st.status(f"Last Action: {last_sig['signal']}", state=last_state):
            st.write(f"Asset: {asset_label}")
            st.write(f"Confidence: {last_sig['final_prob']:.1%}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["price_close"],
            mode="lines",
            name="Price",
            line=dict(color="#2E86C1", width=2),
        ))

        buys = df[df["signal"] == "BUY_CANDIDATE"]
        fig.add_trace(go.Scatter(
            x=buys["timestamp"],
            y=buys["price_close"],
            mode="markers",
            name="Neural Buy",
            marker=dict(symbol="triangle-up", size=15, color="#00FF00"),
        ))

        sells = df[df["signal"] == "SELL_AVOID"]
        fig.add_trace(go.Scatter(
            x=sells["timestamp"],
            y=sells["price_close"],
            mode="markers",
            name="Sell/Avoid",
            marker=dict(symbol="triangle-down", size=12, color="#FF0000"),
        ))

        fig.update_layout(
            title="Live Neural Execution Feed",
            xaxis_title="Time",
            yaxis_title="Price",
            template="plotly_dark",
            height=500,
        )

        st.plotly_chart(fig, use_container_width=True)

        df_display = df.copy()
        df_display["Asset"] = df_display.apply(
            lambda row: format_asset_label(row.get("asset_name"), row.get("ticker")),
            axis=1,
        )
        df_display["Confidence"] = df_display["final_prob"]
        df_display["Rationale"] = df_display["rationale"].apply(clean_rationale)

        st.dataframe(
            df_display[["Asset", "signal", "Confidence", "Rationale"]].rename(
                columns={"signal": "Signal"}
            ),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Confidence": st.column_config.NumberColumn(
                    "Confidence",
                    format="%.1f%%",
                )
            },
        )

with portfolio_tab:
    st.subheader("💼 Portfolio Overview")
    portfolio_state = load_portfolio_state()
    if portfolio_state is None:
        st.info("Portfolio state not found.")
    else:
        timestamp = portfolio_state.get("timestamp")
        if timestamp == 0:
            st.warning("⚠️ Pending Initial Trade")
        else:
            as_of = portfolio_state.get("as_of", "Unknown")
            st.caption(f"As of: {as_of}")

        cash = portfolio_state.get("cash", 0.0)
        positions = portfolio_state.get("positions", [])
        total_value = cash + sum(compute_position_value(p) for p in positions)

        exposure = portfolio_state.get("exposure", {})
        net_exposure = exposure.get("net", 0.0)
        daily_pnl = portfolio_state.get("daily_pnl", 0.0)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Value", f"${total_value:,.2f}")
        col2.metric("Net Exposure", f"${net_exposure:,.2f}")
        col3.metric("Daily PnL", f"${daily_pnl:,.2f}")

        if positions:
            rows = []
            for position in positions:
                asset_label = format_asset_label(
                    position.get("asset_name"), position.get("ticker")
                )
                rows.append(
                    {
                        "Asset": asset_label,
                        "Size": position.get("size") or position.get("quantity") or 0.0,
                        "Entry Price": position.get("entry_price", 0.0),
                        "Current Value": compute_position_value(position),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No active positions.")

with systems_tab:
    st.subheader("⚙️ System Parameters")
    current_values = {key: env_value(key) for key in SETTINGS_KEYS}

    with st.form("settings_form"):
        min_win_rate = st.text_input(
            "ARCOS_MIN_WIN_RATE",
            value=current_values["ARCOS_MIN_WIN_RATE"],
        )
        min_sample_size = st.text_input(
            "ARCOS_MIN_SAMPLE_SIZE",
            value=current_values["ARCOS_MIN_SAMPLE_SIZE"],
        )
        execution_mode = st.selectbox(
            "ARCOS_EXECUTION_MODE",
            ["advisory", "paper", "autopilot"],
            index=["advisory", "paper", "autopilot"].index(
                current_values["ARCOS_EXECUTION_MODE"] or "advisory"
            ),
        )

        submitted = st.form_submit_button("Save Configuration")

    if submitted:
        env_path = os.path.join(os.getcwd(), ".env")
        set_key(env_path, "ARCOS_MIN_WIN_RATE", min_win_rate)
        set_key(env_path, "ARCOS_MIN_SAMPLE_SIZE", min_sample_size)
        set_key(env_path, "ARCOS_EXECUTION_MODE", execution_mode)
        st.success("✅ System Parameters Updated. Swarm restarting...")

    st.caption("Current Settings")
    settings_rows = [
        {"Variable": key, "Value": env_value(key) or "Not set"}
        for key in SETTINGS_KEYS
    ]
    st.table(pd.DataFrame(settings_rows))
