import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import time
import json

# ------------------ FIREBASE INIT ------------------
if not firebase_admin._apps:
    firebase_dict = json.loads(json.dumps(st.secrets["firebase"]))
    cred = credentials.Certificate(firebase_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ------------------ FETCH TRADES ------------------
def fetch_trades():
    docs = db.collection("trades") \
             .order_by("time", direction=firestore.Query.DESCENDING) \
             .stream()
    
    data = []
    for doc in docs:
        d = doc.to_dict()
        data.append({
            "Symbol": d.get("symbol"),
            "Entry": d.get("entry"),
            "Target": d.get("target"),
            "StopLoss": d.get("stopLoss"),
            "Type": d.get("type"),
            "Time": d.get("time")
        })
    
    return pd.DataFrame(data)

# ------------------ UI ------------------
st.title("📈 Live Trade Feed")

# ------------------ ADMIN PANEL ------------------
st.subheader("📤 Send Trade")

password = st.text_input("Admin Password", type="password")

if password:
    if password == st.secrets["general"]["admin_password"]:
        st.success("Admin Access Granted ✅")

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
                "time": firestore.SERVER_TIMESTAMP
            })
            st.success("Trade Sent ✅")
            st.rerun()
    else:
        st.error("Wrong Password ❌")

# ------------------ DISPLAY TRADES ------------------
st.subheader("📊 Latest Trades")

df = fetch_trades()

if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("No trades yet")

# ------------------ AUTO REFRESH ------------------
time.sleep(5)
st.rerun()
