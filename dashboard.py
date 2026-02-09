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

st.markdown(
    """
<style>
:root {
    --arcos-bg: #121417;
    --arcos-panel: #1b1f24;
    --arcos-gold: #d4af37;
    --arcos-text: #e6e6e6;
}
html, body, [class*="stApp"] {
    background-color: var(--arcos-bg);
    color: var(--arcos-text);
}
[data-testid="stSidebar"] {
    background-color: var(--arcos-panel);
}
h1, h2, h3, h4, h5 {
    color: var(--arcos-gold);
}
.stMetric label, .stMetric div {
    color: var(--arcos-text);
}
</style>
""",
    unsafe_allow_html=True,
)

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


def env_value(key):
    return os.environ.get(key, "")


def compute_position_value(position):
    if "current_value" in position:
        return position.get("current_value", 0.0)
    price = position.get("current_price") or position.get("price") or 0.0
    size = position.get("size") or position.get("quantity") or 0.0
    return price * size


df = get_data()

st.title("🦅 ARCOS: Sovereign Intelligence Briefing")

briefing_tab, portfolio_tab, systems_tab = st.tabs(
    ["📡 Intelligence Briefing", "💼 Asset Ledger", "🔧 System Tuning"]
)

with briefing_tab:
    if df.empty:
        st.warning("Waiting for Neural Uplink...")
    else:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df["price_close"],
                mode="lines",
                name="Price",
                line=dict(color="#d4af37", width=2),
            )
        )

        buys = df[df["signal"] == "BUY_CANDIDATE"]
        fig.add_trace(
            go.Scatter(
                x=buys["timestamp"],
                y=buys["price_close"],
                mode="markers",
                name="Neural Buy",
                marker=dict(symbol="triangle-up", size=15, color="#2ecc71"),
            )
        )

        sells = df[df["signal"] == "SELL_AVOID"]
        fig.add_trace(
            go.Scatter(
                x=sells["timestamp"],
                y=sells["price_close"],
                mode="markers",
                name="Sell/Avoid",
                marker=dict(symbol="triangle-down", size=12, color="#e74c3c"),
            )
        )

        fig.update_layout(
            title="Live Neural Execution Feed",
            xaxis_title="Time",
            yaxis_title="Price",
            template="plotly_dark",
            height=500,
        )

        st.plotly_chart(fig, use_container_width=True)

        df_display = df.copy()
        df_display["Asset"] = df_display["asset_name"].fillna("Unknown")
        df_display["Ticker"] = df_display["ticker"].fillna("-")
        df_display["Confidence"] = df_display["final_prob"]
        df_display["Rationale"] = df_display["rationale"].apply(clean_rationale)

        st.dataframe(
            df_display[["Asset", "Ticker", "signal", "Confidence", "Rationale"]].rename(
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
    st.subheader("💼 Asset Ledger")
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

        exposure = portfolio_state.get("exposure", {})
        gross_exposure = exposure.get("gross", 0.0)
        net_exposure = exposure.get("net", 0.0)
        positions = portfolio_state.get("positions", [])

        col1, col2, col3 = st.columns(3)
        col1.metric("Gross Exposure", f"${gross_exposure:,.2f}")
        col2.metric("Net Exposure", f"${net_exposure:,.2f}")
        col3.metric("Position Count", str(len(positions)))

        if positions:
            rows = []
            for position in positions:
                rows.append(
                    {
                        "Asset": position.get("asset_name")
                        or position.get("ticker")
                        or "Unknown",
                        "Size": position.get("size")
                        or position.get("quantity")
                        or 0.0,
                        "Entry Price": position.get("entry_price", 0.0),
                        "Current Value": compute_position_value(position),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No active positions.")

with systems_tab:
    st.subheader("🔧 System Tuning")
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

        submitted = st.form_submit_button("Apply Configuration")

    if submitted:
        env_path = os.path.join(os.getcwd(), ".env")
        set_key(env_path, "ARCOS_MIN_WIN_RATE", min_win_rate)
        set_key(env_path, "ARCOS_MIN_SAMPLE_SIZE", min_sample_size)
        set_key(env_path, "ARCOS_EXECUTION_MODE", execution_mode)
        st.success(
            "✅ Settings saved to .env. Please run 'docker compose restart' to apply changes to the swarm."
        )

    st.caption("Current Settings")
    settings_rows = [
        {"Variable": key, "Value": env_value(key) or "Not set"}
        for key in SETTINGS_KEYS
    ]
    st.table(pd.DataFrame(settings_rows))
