import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import time

# ------------------ FIREBASE INIT ------------------
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ------------------ FETCH DATA ------------------
def fetch_trades():
    docs = db.collection("trades").order_by("time", direction=firestore.Query.DESCENDING).stream()
    
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

placeholder = st.empty()

while True:
    df = fetch_trades()
    
    with placeholder.container():
        st.subheader("Latest Trades")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No trades yet")

    time.sleep(5)