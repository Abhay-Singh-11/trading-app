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
            "id": doc.id,  # ✅ IMPORTANT (for delete)
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

# ------------------ ADMIN LOGIN ------------------
st.subheader("🔐 Admin Panel")

password = st.text_input("Enter Admin Password", type="password")

if password == st.secrets["general"]["admin_password"]:

    st.success("Admin Access Granted ✅")

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
            "time": firestore.SERVER_TIMESTAMP
        })
        st.success("Trade Sent ✅")
        st.rerun()

    # ------------------ DELETE TRADE ------------------
    st.subheader("❌ Delete Trade")

    df = fetch_trades()

    if not df.empty:
        # 🔥 Better UX label
        df["label"] = (
            df["Symbol"].astype(str)
            + " | "
            + df["Type"].astype(str)
            + " | Entry: "
            + df["Entry"].astype(str)
        )

        selected_label = st.selectbox("Select Trade", df["label"])

        selected_id = df[df["label"] == selected_label]["id"].values[0]

        if st.button("Delete Trade"):
            db.collection("trades").document(selected_id).delete()
            st.success("Trade Deleted ✅")
            st.rerun()
    else:
        st.info("No trades to delete")

elif password:
    st.error("Wrong Password ❌")

# ------------------ DISPLAY TRADES ------------------
st.subheader("📊 Latest Trades")

df = fetch_trades()

if not df.empty:
    st.dataframe(df.drop(columns=["id"]), use_container_width=True)
else:
    st.info("No trades yet")

# ------------------ AUTO REFRESH ------------------
time.sleep(5)
st.rerun()
