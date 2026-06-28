# V53.1 STABLE AI TRADER
# This is a starter stable template based on your V53.
# Replace with your full strategy logic as desired.

import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="V53.1 STABLE", layout="wide")
st.title("🏆 V53.1 STABLE AI TRADER")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY")

COINS = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]

if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=30)
def load_data(symbol):
    if not API_KEY:
        return None
    try:
        r = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol":symbol,
                "interval":"15min",
                "outputsize":200,
                "apikey":API_KEY
            },
            timeout=10
        ).json()

        if "values" not in r:
            return None

        df = pd.DataFrame(r["values"]).iloc[::-1].reset_index(drop=True)
        for c in ["open","high","low","close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna()
        if len(df) < 30:
            return None
        return df
    except Exception:
        return None

results=[]

for coin in COINS:
    df = load_data(coin)

    if df is None:
        results.append({
            "Coin":coin,
            "Signal":"NO DATA",
            "Score":0
        })
        continue

    price=df["close"].iloc[-1]
    support=df["low"].rolling(20).min().iloc[-1]
    resistance=df["high"].rolling(20).max().iloc[-1]

    signal="WAIT"
    score=40

    if price <= support*1.005:
        signal="LONG"
        score=75
    elif price >= resistance*0.995:
        signal="SHORT"
        score=75

    results.append({
        "Coin":coin,
        "Signal":signal,
        "Score":score
    })

table=pd.DataFrame(results)

st.dataframe(table, use_container_width=True)

valid=table[table["Signal"].isin(["LONG","SHORT"])]

if not valid.empty:
    best=valid.sort_values("Score", ascending=False).iloc[0]
    st.success(f"Best Trade: {best['Coin']} ({best['Signal']})")
else:
    st.info("Kein gültiges Setup gefunden.")
