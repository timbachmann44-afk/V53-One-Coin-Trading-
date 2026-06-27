import streamlit as st
import requests
import pandas as pd
import numpy as np

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V53 INSTITUTIONAL AI", layout="wide")

st.title("🏆 V53 INSTITUTIONAL AI TRADER (ONLY BEST TRADE)")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh Institutional Scan"):
    st.cache_data.clear()
    st.rerun()

# =========================
# UI
# =========================
st.markdown("""
<style>

.stApp {
    background:#05070D;
    color:#EAEAEA;
}

h1,h2,h3 {
    color:#00E5FF;
}

.card {
    background:#0B1220;
    padding:14px;
    border-radius:14px;
    margin-bottom:12px;
    border:1px solid #1f2937;
}

</style>
""", unsafe_allow_html=True)

# =========================
# COINS
# =========================
coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]

selected = st.sidebar.multiselect("Coins", coins, default=coins)

# =========================
# DATA LOADER
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

        df = pd.DataFrame(r["values"])
        df = df.iloc[::-1]

        for c in ["open","high","low","close"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df

    except:
        return None

# =========================
# STRUCTURE
# =========================
def structure(df):

    if df is None or len(df) < 30:
        return None, None, None, None, None

    price = df["close"].iloc[-1]
    support = df["low"].rolling(20).min().iloc[-1]
    resistance = df["high"].rolling(20).max().iloc[-1]
    atr = (df["high"] - df["low"]).rolling(20).mean().iloc[-1]
    momentum = df["close"].diff(5).mean()

    return price, support, resistance, atr, momentum

# =========================
# ZONES
# =========================
def entry_zone(price, support, resistance, atr):

    zone_size = atr * 0.6

    if support <= price <= support + zone_size:
        return "LONG_ZONE"
    elif resistance - zone_size <= price <= resistance:
        return "SHORT_ZONE"
    else:
        return "NO_ZONE"

# =========================
# INSTITUTIONAL ENGINE
# =========================
def engine(price, support, resistance, atr, momentum, zone):

    score = 50
    reasons = []

    # =========================
    # TREND FILTER
    # =========================
    trend = "BULLISH" if momentum > 0 else "BEARISH"

    if trend == "BULLISH":
        score += 10
        reasons.append("Bullish trend")
    else:
        score -= 10
        reasons.append("Bearish trend")

    # =========================
    # SIGNAL LOGIC
    # =========================
    if zone == "LONG_ZONE":
        signal = "LONG"
        entry_low = support
        entry_high = support + atr
        sl = support - atr
        tp = resistance
        score += 30
        reasons.append("Long institutional zone")

    elif zone == "SHORT_ZONE":
        signal = "SHORT"
        entry_low = resistance - atr
        entry_high = resistance
        sl = resistance + atr
        tp = support
        score += 30
        reasons.append("Short institutional zone")

    else:
        signal = "NO TRADE"
        entry_low = None
        entry_high = None
        sl = None
        tp = None
        score -= 20
        reasons.append("No institutional setup")

    # =========================
    # RR CALC
    # =========================
    rr = 0

    if entry_low is not None:
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
# SCAN ALL COINS
# =========================
results = []

for coin in selected:

    df = load_data(coin)

    price, support, resistance, atr, momentum = structure(df)

    zone = entry_zone(price, support, resistance, atr)

    signal, trend, e_low, e_high, sl, tp, rr, score, reasons = engine(
        price, support, resistance, atr, momentum, zone
    )

    results.append({
        "Coin": coin,
        "Signal": signal,
        "Trend": trend,
        "Zone": zone,
        "Entry": f"{round(e_low,2) if e_low else None} - {round(e_high,2) if e_high else None}",
        "SL": round(sl,2) if sl else None,
        "TP": round(tp,2) if tp else None,
        "RR": rr,
        "Score": score,
        "Reasons": reasons
    })

df = pd.DataFrame(results)

# =========================
# CLEAN FILTER (INSTITUTIONAL RULE)
# =========================
df_valid = df[df["Signal"] != "NO TRADE"]

if df_valid.empty:
    st.warning("No institutional-grade setup found right now.")
    st.stop()

# =========================
# ONLY TOP TRADE
# =========================
best = df_valid.sort_values("Score", ascending=False).iloc[0]

# QUALITY GATE (VERY IMPORTANT)
if best["Score"] < 70:
    st.warning("No high-quality institutional trade available.")
    st.stop()

# =========================
# KPI
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("📊 ACTIVE SETUPS", len(df_valid))
c2.metric("🔥 BEST SCORE", best["Score"])
c3.metric("🎯 SELECTED TRADE", best["Coin"])

# =========================
# FINAL OUTPUT (ONLY 1 TRADE)
# =========================
st.success("🏆 INSTITUTIONAL TRADE OF THE DAY")

st.markdown(f"""
<div class="card">

<h2>{best['Coin']} – {best['Signal']}</h2>

📊 Trend: {best['Trend']}<br>
📍 Zone: {best['Zone']}<br>

<hr>

🎯 Entry: {best['Entry']}<br>
🛑 SL: {best['SL']}<br>
📈 TP: {best['TP']}<br>

<hr>

📊 RR: {best['RR']}<br>
🧠 Score: {best['Score']}

<hr>

🧠 AI REASONING:<br>
{"<br>".join(["- " + x for x in best["Reasons"]])}

</div>
""", unsafe_allow_html=True)