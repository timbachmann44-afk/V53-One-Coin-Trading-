import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
import time

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="V53 INSTITUTIONAL AI", layout="wide")

st.title("🏆 V53 INSTITUTIONAL AI DASHBOARD")

API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", None)

coins = ["BTC/USD","ETH/USD","XRP/USD","SOL/USD","ADA/USD","DOGE/USD","BNB/USD"]
selected = st.sidebar.multiselect("Coins", coins, default=coins)

# =========================
# STYLING
# =========================
st.markdown("""
<style>
.stApp { background:#05070D; color:#EAEAEA; }
h1,h2,h3 { color:#00E5FF; }
.card {
    background:#0B1220;
    padding:16px;
    border-radius:14px;
    border:1px solid #1f2937;
}
</style>
""", unsafe_allow_html=True)

# =========================
# REFRESH
# =========================
if st.button("🔄 Refresh Scan"):
    st.cache_data.clear()
    st.rerun()

# =========================
# SAFE API CALL (RETRY)
# =========================
def fetch_data(symbol, retries=3):

    if not API_KEY:
        return None

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "15min",
        "outputsize": 200,
        "apikey": API_KEY
    }

    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10).json()

            if "values" not in r:
                time.sleep(1)
                continue

            df = pd.DataFrame(r["values"]).iloc[::-1]

            for c in ["open","high","low","close"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")

            df = df.dropna()

            if len(df) < 50:
                return None

            return df

        except:
            time.sleep(1)

    return None

# =========================
# INDICATORS
# =========================
def indicators(df):

    try:
        df = df.copy()

        df["ema20"] = EMAIndicator(df["close"], 20).ema_indicator()
        df["ema50"] = EMAIndicator(df["close"], 50).ema_indicator()
        df["rsi"] = RSIIndicator(df["close"], 14).rsi()

        atr = AverageTrueRange(df["high"], df["low"], df["close"], 14)
        df["atr"] = atr.average_true_range()

        df["momentum"] = df["close"].diff(5)

        return df

    except:
        return None

# =========================
# STRUCTURE
# =========================
def structure(df):

    try:
        price = df["close"].iloc[-1]

        support = df["low"].rolling(20).min().iloc[-1]
        resistance = df["high"].rolling(20).max().iloc[-1]

        return price, support, resistance

    except:
        return None, None, None

# =========================
# ZONES
# =========================
def zone(price, support, resistance, atr):

    try:
        if any(v is None or np.isnan(v) for v in [price, support, resistance, atr]):
            return "NO_ZONE"

        zone_size = atr * 0.6

        if support <= price <= support + zone_size:
            return "LONG"
        elif resistance - zone_size <= price <= resistance:
            return "SHORT"
        else:
            return "NO_ZONE"

    except:
        return "NO_ZONE"

# =========================
# SCORE ENGINE
# =========================
def score_engine(df, price, support, resistance, atr):

    try:
        last = df.iloc[-1]

        score = 50
        reasons = []

        ema20 = last["ema20"]
        ema50 = last["ema50"]
        rsi = last["rsi"]
        momentum = last["momentum"]

        trend = "BULLISH" if ema20 > ema50 else "BEARISH"

        # Trend filter
        if trend == "BULLISH":
            score += 15
            reasons.append("EMA trend bullish")
        else:
            score -= 15
            reasons.append("EMA trend bearish")

        # EMA confirmation
        if ema20 > ema50:
            score += 10
        else:
            score -= 10

        # RSI filter
        if 40 <= rsi <= 65:
            score += 10
            reasons.append("RSI healthy zone")
        elif rsi > 70:
            score -= 10
        elif rsi < 30:
            score += 5

        # Momentum
        if momentum > 0:
            score += 10
        else:
            score -= 10

        # Zone logic
        z = zone(price, support, resistance, atr)

        if z == "LONG":
            entry = support
            sl = support - atr
            tp = resistance
            score += 20
            reasons.append("Long liquidity zone")

        elif z == "SHORT":
            entry = resistance
            sl = resistance + atr
            tp = support
            score += 20
            reasons.append("Short liquidity zone")

        else:
            return None

        risk = abs(entry - sl)
        reward = abs(tp - entry)

        rr = round(reward / risk, 2) if risk != 0 else 0

        if rr > 2:
            score += 10
        elif rr < 1.2:
            score -= 10

        score = max(0, min(100, score))

        return {
            "trend": trend,
            "zone": z,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": rr,
            "score": score,
            "reasons": reasons
        }

    except:
        return None

# =========================
# CHART
# =========================
def chart(df, coin):

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    ))

    fig.add_trace(go.Scatter(x=df.index, y=df["ema20"], name="EMA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df["ema50"], name="EMA50"))

    fig.update_layout(
        title=f"{coin} Chart",
        template="plotly_dark",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================
# SCAN
# =========================
results = []

for coin in selected:

    df = fetch_data(coin)

    if df is None:
        st.warning(f"{coin}: no data")
        continue

    df = indicators(df)

    if df is None:
        continue

    price, support, resistance = structure(df)

    atr = df["atr"].iloc[-1]

    res = score_engine(df, price, support, resistance, atr)

    if res is None:
        continue

    results.append({
        "Coin": coin,
        **res
    })

# =========================
# RESULTS
# =========================
if not results:
    st.warning("No valid setups found.")
    st.stop()

df = pd.DataFrame(results)

best = df.sort_values("score", ascending=False).iloc[0]

# =========================
# KPI
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("📊 SETUPS", len(df))
c2.metric("🔥 BEST SCORE", best["score"])
c3.metric("🎯 TOP COIN", best["Coin"])

st.markdown("## 🏆 Trade of the Day")

st.markdown(f"""
<div class="card">

<h2>{best['Coin']} – {best['zone']}</h2>

Trend: {best['trend']}  
Entry: {round(best['entry'],4)}  
SL: {round(best['sl'],4)}  
TP: {round(best['tp'],4)}  

RR: {best['rr']}  
Score: {best['score']}

<b>Reasons:</b><br>
{"<br>".join(["- "+r for r in best["reasons"]])}

</div>
""", unsafe_allow_html=True)

st.markdown("## 📊 Ranking")
st.dataframe(df.sort_values("score", ascending=False))

# =========================
# CHART BEST COIN
# =========================
best_coin_df = fetch_data(best["Coin"])
best_coin_df = indicators(best_coin_df)

chart(best_coin_df, best["Coin"])
