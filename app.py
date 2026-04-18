import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import time
import json
import requests

# ------------------ FIREBASE INIT ------------------
if not firebase_admin._apps:
    firebase_dict = json.loads(json.dumps(st.secrets["firebase"]))
    cred = credentials.Certificate(firebase_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ------------------ TELEGRAM ------------------
def send_telegram(msg):
    try:
        token = st.secrets["general"]["telegram_token"]
        chat_id = st.secrets["general"]["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": msg})
    except:
        pass

# ------------------ FETCH TRADES ------------------
def fetch_trades():
    docs = db.collection("trades") \
             .order_by("time", direction=firestore.Query.DESCENDING) \
             .stream()
    
    data = []
    for doc in docs:
        d = doc.to_dict()
        data.append({
            "id": doc.id,
            "Symbol": d.get("symbol"),
            "Entry": d.get("entry"),
            "Target": d.get("target"),
            "StopLoss": d.get("stopLoss"),
            "Type": d.get("type"),
            "Status": d.get("status", "RUNNING"),
            "Time": d.get("time")
        })
    
    return pd.DataFrame(data)

# ------------------ UI ------------------
st.title("📈 Pro Trade Panel")

# ------------------ LOGIN ------------------
password = st.text_input("Admin Password", type="password")
is_admin = password == st.secrets["general"]["admin_password"]

if is_admin:
    st.success("Admin Access ✅")

    # ------------------ ADD TRADE ------------------
    st.subheader("📤 Send Trade")

    symbol = st.text_input("Symbol")
    entry = st.number_input("Entry")
    target = st.number_input("Target")
    stoploss = st.number_input("StopLoss")
    trade_type = st.selectbox("Type", ["BUY", "SELL"])

    if st.button("Send Trade"):
        db.collection("trades").add({
            "symbol": symbol,
            "entry": entry,
            "target": target,
            "stopLoss": stoploss,
            "type": trade_type,
            "status": "RUNNING",
            "time": firestore.SERVER_TIMESTAMP
        })

        send_telegram(f"📢 NEW TRADE\n{trade_type} {symbol}\nEntry: {entry}\nTarget: {target}\nSL: {stoploss}")
        st.success("Trade Sent ✅")
        st.rerun()

elif password:
    st.error("Wrong Password ❌")

# ------------------ DISPLAY ------------------
st.subheader("📊 Live Trades")

df = fetch_trades()

if not df.empty:
    df_display = df.drop(columns=["id", "Time"], errors="ignore")

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No trades yet")

# ------------------ ANALYTICS ------------------
st.subheader("📊 Performance Dashboard")

completed = df[df["Status"].isin(["TARGET HIT", "SL HIT"])]

if not completed.empty:
    total_trades = len(completed)
    wins = len(completed[completed["Status"] == "TARGET HIT"])
    losses = len(completed[completed["Status"] == "SL HIT"])

    win_rate = (wins / total_trades) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trades", total_trades)
    col2.metric("Wins", wins)
    col3.metric("Losses", losses)

    st.metric("🟢 Win Rate (%)", f"{win_rate:.2f}%")

    # ------------------ DAILY PERFORMANCE ------------------
    st.subheader("📈 Daily Performance")

    df_time = df.copy()
    df_time["Time"] = pd.to_datetime(df_time["Time"], errors="coerce")
    df_time["Date"] = df_time["Time"].dt.date

    daily = df_time[df_time["Status"].isin(["TARGET HIT", "SL HIT"])]

    if not daily.empty:
        summary = daily.groupby(["Date", "Status"]).size().unstack(fill_value=0)
        st.dataframe(summary, use_container_width=True)
    else:
        st.info("No completed trades for daily stats")

else:
    st.info("No completed trades yet")

# ------------------ ADMIN ACTIONS ------------------
if is_admin and not df.empty:

    st.subheader("✏️ Edit / Manage Trade")

    df["label"] = df["Symbol"] + " | " + df["Type"] + " | Entry: " + df["Entry"].astype(str)

    selected_label = st.selectbox("Select Trade", df["label"])
    selected_row = df[df["label"] == selected_label].iloc[0]
    selected_id = selected_row["id"]

    new_target = st.number_input("New Target", value=float(selected_row["Target"]))
    new_sl = st.number_input("New StopLoss", value=float(selected_row["StopLoss"]))
    new_status = st.selectbox("Status", ["RUNNING", "TARGET HIT", "SL HIT"])

    if st.button("Update Trade"):
        db.collection("trades").document(selected_id).update({
            "target": new_target,
            "stopLoss": new_sl,
            "status": new_status
        })

        send_telegram(f"✏️ UPDATE\n{selected_row['Symbol']}\nStatus: {new_status}")
        st.success("Trade Updated ✅")
        st.rerun()

    if st.button("Delete Trade"):
        db.collection("trades").document(selected_id).delete()
        send_telegram(f"❌ DELETED\n{selected_row['Symbol']}")
        st.success("Deleted ✅")
        st.rerun()

# ------------------ AUTO REFRESH ------------------
time.sleep(5)
st.rerun()
