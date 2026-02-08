import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import time
import os
import json

st.set_page_config(page_title="ARCOS War Room", layout="wide", page_icon="⚔️")
DB_FILE = os.environ.get("ARCOS_DB_PATH", "/app/workspace/arcos_vault.db")
WORKSPACE_ROOT = os.environ.get("ARCOS_WORKSPACE", "/app/workspace")
SETTINGS_KEYS = [
    "SMTP_USER",
    "SMTP_PASS",
    "ALERT_RECIPIENT",
    "ARCOS_EXECUTION_MODE",
    "ARCOS_WORKSPACE",
    "ARCOS_DB_PATH",
    "ARCOS_MIN_SAMPLE_SIZE",
    "ARCOS_MIN_WIN_RATE",
    "ARCOS_MAX_POSITION_CAP",
    "ARCOS_MAX_GROSS_EXPOSURE",
]

def mask_setting(value):
    if not value:
        return "Not set"
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"

def clean_rationale(text):
    if not isinstance(text, str):
        return ""
    return text.split("|", 1)[0].strip()

# --- Auto Refresh (5s) ---
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 5:
    st.session_state.last_refresh = time.time()
    st.rerun()

def get_data():
    if not os.path.exists(DB_FILE): return pd.DataFrame()
    conn = sqlite3.connect(DB_FILE, timeout=10)
    df = pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 200", conn)
    conn.close()
    return df

df = get_data()

st.title("⚔️ ARCOS: Deep Neural War Room")
st.sidebar.header("⚙️ Settings")
settings_rows = []
for key in SETTINGS_KEYS:
    value = os.environ.get(key, "")
    if key == "SMTP_PASS":
        value = mask_setting(value)
    settings_rows.append({"Variable": key, "Value": value or "Not set"})
st.sidebar.table(pd.DataFrame(settings_rows))

if not df.empty:
    # Top Metrics
    last_sig = df.iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Target", last_sig['ticker'])
    col2.metric("Last Price", f"${last_sig['price_close']:.2f}")
    col3.metric("Confidence", f"{last_sig['final_prob']:.1%}")
    
    # Dynamic Color for Signal
    sig_color = "normal"
    if "BUY" in last_sig['signal']: sig_color = "off" # Greenish highlight logic
    col4.metric("Action", last_sig['signal'])

    # --- THE CHART ---
    # We reconstruct the "Tape" from your database
    fig = go.Figure()

    # 1. Price Line
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['price_close'],
        mode='lines',
        name='Price',
        line=dict(color='#2E86C1', width=2)
    ))

    # 2. Buy Signals (Green Triangles)
    buys = df[df['signal'] == 'BUY_CANDIDATE']
    fig.add_trace(go.Scatter(
        x=buys['timestamp'], 
        y=buys['price_close'],
        mode='markers',
        name='Neural Buy',
        marker=dict(symbol='triangle-up', size=15, color='#00FF00')
    ))

    # 3. Sell/Avoid Signals (Red Triangles)
    sells = df[df['signal'] == 'SELL_AVOID']
    fig.add_trace(go.Scatter(
        x=sells['timestamp'], 
        y=sells['price_close'],
        mode='markers',
        name='Sell/Avoid',
        marker=dict(symbol='triangle-down', size=12, color='#FF0000')
    ))

    fig.update_layout(
        title="Live Neural Execution Feed",
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark",
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent Log
    st.subheader("📝 Neural Log")
    df_display = df.copy()
    df_display["Confidence"] = df_display["final_prob"] * 100
    df_display["rationale"] = df_display["rationale"].apply(clean_rationale)
    st.dataframe(
        df_display[['timestamp', 'ticker', 'signal', 'Confidence', 'rationale']],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Confidence": st.column_config.NumberColumn(
                "Confidence",
                format="%.1f%%",
            )
        },
    )

else:
    st.warning("Waiting for Neural Uplink...")

st.subheader("🧾 Portfolio State")
portfolio_path = os.path.join(WORKSPACE_ROOT, "portfolio_state.json")
if os.path.exists(portfolio_path):
    with open(portfolio_path, "r", encoding="utf-8") as f:
        portfolio_state = json.load(f)

    timestamp = portfolio_state.get("timestamp")
    if timestamp == 0:
        st.warning("⚠️ Pending Initial Trade")
    else:
        as_of = portfolio_state.get("as_of", "Unknown")
        st.caption(f"As of: {as_of}")

    exposure = portfolio_state.get("exposure", {})
    gross_exposure = exposure.get("gross", 0.0)
    net_exposure = exposure.get("net", 0.0)
    exp_col1, exp_col2 = st.columns(2)
    exp_col1.metric("Gross Exposure", f"${gross_exposure:,.2f}")
    exp_col2.metric("Net Exposure", f"${net_exposure:,.2f}")

    positions = portfolio_state.get("positions", [])
    if positions:
        st.table(pd.DataFrame(positions))
    else:
        st.info("No active positions.")
else:
    st.info("Portfolio state not found.")

st.subheader("📌 Audit Manifests")
manifest_dir = os.path.join(WORKSPACE_ROOT, "official", "manifests")
if os.path.isdir(manifest_dir):
    manifest_files = sorted([f for f in os.listdir(manifest_dir) if f.endswith(".json")], reverse=True)[:10]
    if manifest_files:
        selected = st.selectbox("Select manifest", manifest_files)
        with open(os.path.join(manifest_dir, selected), "r", encoding="utf-8") as f:
            st.json(json.load(f))
    else:
        st.info("No manifests available.")
else:
    st.info("Manifest directory not found.")
