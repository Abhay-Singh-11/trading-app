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

# ------------------ P&L CALC ------------------
def calculate_pnl(row):
    if row["Status"] == "TARGET HIT":
        return row["Target"] - row["Entry"] if row["Type"] == "BUY" else row["Entry"] - row["Target"]
    elif row["Status"] == "SL HIT":
        return row["StopLoss"] - row["Entry"] if row["Type"] == "BUY" else row["Entry"] - row["StopLoss"]
    return 0

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

# ------------------ DISPLAY ------------------
st.subheader("📊 Live Trades")

df = fetch_trades()

if not df.empty:

    # P&L
    df["PnL"] = df.apply(calculate_pnl, axis=1)

    st.dataframe(df.drop(columns=["id"]), use_container_width=True)

    # ------------------ ADMIN ACTIONS ------------------
    if is_admin:

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

        # ------------------ DELETE ------------------
        if st.button("Delete Trade"):
            db.collection("trades").document(selected_id).delete()
            send_telegram(f"❌ DELETED\n{selected_row['Symbol']}")
            st.success("Deleted ✅")
            st.rerun()

else:
    if password:
        st.error("Wrong Password ❌")

# ------------------ AUTO REFRESH ------------------
time.sleep(5)
st.rerun()
