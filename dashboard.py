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

if not df.empty:
    # Top Metrics
    last_sig = df.iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Target", last_sig['ticker'])
    col2.metric("Last Price", f"${last_sig['price_close']:.2f}")
    col3.metric("Neural Confidence", f"{last_sig['final_prob']:.0%}")
    
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
    st.dataframe(df[['timestamp', 'ticker', 'signal', 'final_prob', 'rationale']], hide_index=True, use_container_width=True)

else:
    st.warning("Waiting for Neural Uplink...")

st.subheader("🧾 Portfolio State")
portfolio_path = os.path.join(WORKSPACE_ROOT, "portfolio_state.json")
if os.path.exists(portfolio_path):
    with open(portfolio_path, "r", encoding="utf-8") as f:
        st.json(json.load(f))
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
