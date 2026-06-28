import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="V53 INSTITUTIONAL AI", layout="wide")

st.title("🏆 V53 INSTITUTIONAL AI TRADER")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]
selected = st.sidebar.multiselect("Coins", coins, default=coins)

# =========================
# DATA
# =========================
@st.cache_data(ttl=30)
def load_data(symbol):

    if not API_KEY:
        return None

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "15min",
        "outputsize": 200,
        "apikey": API_KEY
    }

    try:
        r = requests.get(url, params=params, timeout=10).json()

        if "values" not in r:
            return None

        df = pd.DataFrame(r["values"]).iloc[::-1]

        for c in ["open","high","low","close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.dropna()

    except:
        return None

# =========================
# STRUCTURE
# =========================
def structure(df):
    if df is None or len(df) < 30:
        return None

    price = df["close"].iloc[-1]
    support = df["low"].rolling(20).min().iloc[-1]
    resistance = df["high"].rolling(20).max().iloc[-1]
    atr = (df["high"] - df["low"]).rolling(20).mean().iloc[-1]
    momentum = df["close"].diff(5).mean()

    return price, support, resistance, atr, momentum

# =========================
# ZONE
# =========================
def entry_zone(price, support, resistance, atr):

    if None in [price, support, resistance, atr]:
        return None

    zone_size = atr * 0.6

    if support <= price <= support + zone_size:
        return "LONG_ZONE"
    elif resistance - zone_size <= price <= resistance:
        return "SHORT_ZONE"
    else:
        return "NO_ZONE"

# =========================
# ENGINE
# =========================
def engine(price, support, resistance, atr, momentum, zone):

    if None in [price, support, resistance, atr, momentum, zone]:
        return None

    score = 50
    reasons = []

    trend = "BULLISH" if momentum > 0 else "BEARISH"

    if trend == "BULLISH":
        score += 10
        reasons.append("Bullish trend")
    else:
        score -= 10
        reasons.append("Bearish trend")

    if zone == "LONG_ZONE":
        signal = "LONG"
        entry_low = support
        entry_high = support + atr
        sl = support - atr
        tp = resistance
        score += 30
        reasons.append("Long zone")

    elif zone == "SHORT_ZONE":
        signal = "SHORT"
        entry_low = resistance - atr
        entry_high = resistance
        sl = resistance + atr
        tp = support
        score += 30
        reasons.append("Short zone")

    else:
        return None

    entry = (entry_low + entry_high) / 2
    risk = abs(entry - sl)
    reward = abs(tp - entry)

    rr = round(reward / risk, 2) if risk != 0 else 0

    if rr > 2:
        score += 10
    elif rr < 1.2:
        score -= 10

    score = max(0, min(100, score))

    return signal, trend, entry_low, entry_high, sl, tp, rr, score, reasons

# =========================
# SCAN
# =========================
results = []

for coin in selected:

    df = load_data(coin)
    parsed = structure(df)

    if not parsed:
        continue

    price, support, resistance, atr, momentum = parsed
    zone = entry_zone(price, support, resistance, atr)

    result = engine(price, support, resistance, atr, momentum, zone)

    if not result:
        continue

    signal, trend, e_low, e_high, sl, tp, rr, score, reasons = result

    results.append({
        "Coin": coin,
        "Signal": signal,
        "Trend": trend,
        "Zone": zone,
        "Entry": f"{round(e_low,2)} - {round(e_high,2)}",
        "SL": round(sl,2),
        "TP": round(tp,2),
        "RR": rr,
        "Score": score,
        "Reasons": reasons
    })

df = pd.DataFrame(results)

if df.empty:
    st.warning("No setup found.")
    st.stop()

best = df.sort_values("Score", ascending=False).iloc[0]

if best["Score"] < 70:
    st.warning("No high-quality trade.")
    st.stop()

# =========================
# OUTPUT
# =========================
st.success("🏆 BEST INSTITUTIONAL TRADE")

st.markdown(f"""
### {best['Coin']} – {best['Signal']}

Trend: {best['Trend']}  
Zone: {best['Zone']}  

Entry: {best['Entry']}  
SL: {best['SL']}  
TP: {best['TP']}  

RR: {best['RR']}  
Score: {best['Score']}

**Reasons:**
""" + "\n".join([f"- {r}" for r in best["Reasons"]]))