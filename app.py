import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import random

st.set_page_config(page_title="Paper Trader Pro", layout="wide")

# --- 1. CORE FUNCTIONS & CACHING ---
@st.cache_data(ttl=60, show_spinner=False)
def get_live_price(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        if hist.empty: return None
        return float(hist['Close'].iloc[-1])
    except:
        return None

DATA_FILE = "trading_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            df = pd.DataFrame(data.get("portfolio", []))
            if df.empty or "Ticker" not in df.columns:
                df = pd.DataFrame(columns=["Ticker", "Shares", "Total Invested"])
            opt_data = data.get("optimizer", {})
            return data.get("cash", 10000000.00), df, opt_data
    else:
        return 10000000.00, pd.DataFrame(columns=["Ticker", "Shares", "Total Invested"]), {}

def save_data(cash, portfolio_df, opt_data):
    data = {
        "cash": cash, 
        "portfolio": portfolio_df.to_dict("records"),
        "optimizer": opt_data
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

if "cash" not in st.session_state:
    st.session_state.cash, st.session_state.portfolio, st.session_state.optimizer = load_data()


# --- 2. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Navigation")
    app_mode = st.radio("Choose Mode:", [
        "📈 Live Trading", 
        "🎮 Market Replay Academy", 
        "⚖️ Portfolio Optimizer",
        "🔮 Cycle & Value Screener" # NEW MODE ADDED
    ])
    
    st.divider()
    st.header("⚙️ Settings")
    if st.button("🚨 Reset Live Account (₹1 Crore)"):
        st.session_state.cash = 10000000.00
        st.session_state.portfolio = pd.DataFrame(columns=["Ticker", "Shares", "Total Invested"])
        st.session_state.optimizer = {}
        save_data(st.session_state.cash, st.session_state.portfolio, st.session_state.optimizer)
        st.cache_data.clear()
        st.success("Account reset to ₹1 Crore!")
        st.rerun()

# ==========================================
# MODE 1: LIVE TRADING SIMULATOR
# ==========================================
if app_mode == "📈 Live Trading":
    st.title("📈 My Paper Trading Simulator")
    # ... (Keep all your existing Mode 1 code here)
    portfolio = st.session_state.portfolio
    live_portfolio = pd.DataFrame()
    total_stock_value = 0.0

    if not portfolio.empty:
        with st.spinner("Calculating live portfolio value..."):
            live_portfolio = portfolio.copy()
            live_prices = []
            for ticker in live_portfolio['Ticker']:
                price = get_live_price(ticker)
                live_prices.append(price if price is not None else 0.0)
                    
            live_portfolio['Live Price'] = live_prices
            live_portfolio['Current Value'] = live_portfolio['Shares'] * live_portfolio['Live Price']
            live_portfolio['Total Invested'] = pd.to_numeric(live_portfolio['Total Invested'])
            live_portfolio['Profit/Loss (₹)'] = live_portfolio['Current Value'] - live_portfolio['Total Invested']
            live_portfolio['Profit/Loss (%)'] = (live_portfolio['Profit/Loss (₹)'] / live_portfolio['Total Invested']) * 100
            total_stock_value = live_portfolio['Current Value'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Virtual Cash Available", f"₹{st.session_state.cash:,.2f}")
    col2.metric("Total Asset Value", f"₹{total_stock_value:,.2f}")
    col3.metric("Total Account Value", f"₹{(st.session_state.cash + total_stock_value):,.2f}")

    st.divider()
    st.header("Trading Terminal")
    tab1, tab2 = st.tabs(["🟢 Buy", "🔴 Sell"])

    with tab1: 
        buy_ticker = st.text_input("Ticker to Buy (e.g., RELIANCE.NS, BTC-USD):", key="buy_ticker").upper()
        if buy_ticker:
            current_price = get_live_price(buy_ticker)
            if current_price is None:
                st.error(f"⚠️ No market data found for '{buy_ticker}'. Check spelling (add .NS for India).")
            else:
                st.success(f"Current Price of {buy_ticker}: **₹{current_price:,.2f}**")
                shares_to_buy = st.number_input(f"Shares/Coins to Buy", min_value=0.01, step=1.0)
                total_cost = shares_to_buy * current_price
                st.write(f"**Estimated Cost:** ₹{total_cost:,.2f}")
                
                if st.button("Execute Buy"):
                    if total_cost > st.session_state.cash:
                        st.error("Insufficient funds!")
                    else:
                        st.session_state.cash -= total_cost
                        if buy_ticker in st.session_state.portfolio['Ticker'].values:
                            idx = st.session_state.portfolio.index[st.session_state.portfolio['Ticker'] == buy_ticker][0]
                            st.session_state.portfolio.at[idx, 'Shares'] += shares_to_buy
                            st.session_state.portfolio.at[idx, 'Total Invested'] += total_cost
                        else:
                            new_trade = pd.DataFrame([{"Ticker": buy_ticker, "Shares": shares_to_buy, "Total Invested": total_cost}])
                            st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_trade], ignore_index=True)
                        save_data(st.session_state.cash, st.session_state.portfolio, st.session_state.optimizer)
                        st.success(f"Bought {shares_to_buy} of {buy_ticker}.")
                        st.rerun()

    with tab2: 
        if not st.session_state.portfolio.empty:
            owned_tickers = st.session_state.portfolio['Ticker'].tolist()
            sell_ticker = st.selectbox("Ticker to Sell:", owned_tickers)
            idx = st.session_state.portfolio.index[st.session_state.portfolio['Ticker'] == sell_ticker][0]
            owned_shares = float(st.session_state.portfolio.at[idx, 'Shares'])
            total_invested = float(st.session_state.portfolio.at[idx, 'Total Invested'])
            
            current_price = get_live_price(sell_ticker)
            if current_price:
                st.success(f"Current Market Price: **₹{current_price:,.2f}**")
                shares_to_sell = st.number_input(f"Amount to Sell", min_value=0.01, max_value=owned_shares, step=1.0)
                proceeds = shares_to_sell * current_price
                
                if st.button("Execute Sell"):
                    st.session_state.cash += proceeds
                    avg_cost = total_invested / owned_shares
                    st.session_state.portfolio.at[idx, 'Shares'] -= shares_to_sell
                    st.session_state.portfolio.at[idx, 'Total Invested'] -= (avg_cost * shares_to_sell)
                    if st.session_state.portfolio.at[idx, 'Shares'] <= 0.0001:
                        st.session_state.portfolio = st.session_state.portfolio.drop(idx).reset_index(drop=True)
                    save_data(st.session_state.cash, st.session_state.portfolio, st.session_state.optimizer)
                    st.rerun()
                    
    st.divider()
    st.header("My Open Positions (Live)")
    if not live_portfolio.empty:
        formatted_portfolio = live_portfolio.style.format({
            "Shares": "{:.4f}", "Total Invested": "₹{:,.2f}", "Live Price": "₹{:,.2f}",
            "Current Value": "₹{:,.2f}", "Profit/Loss (₹)": "₹{:,.2f}", "Profit/Loss (%)": "{:,.2f}%"
        })
        st.dataframe(formatted_portfolio, use_container_width=True, hide_index=True)

# ==========================================
# MODE 2 & 3: ACADEMY & OPTIMIZER 
# ==========================================
# (For brevity in this text box, paste your existing Mode 2 and Mode 3 code here)
elif app_mode == "🎮 Market Replay Academy":
    st.title("🎮 Market Replay Academy")
    st.write("(Your existing Academy code goes here...)")
    
elif app_mode == "⚖️ Portfolio Optimizer":
    st.title("⚖️ Mathematical Portfolio Optimizer")
    st.write("(Your existing Optimizer code goes here...)")


# ==========================================
# MODE 4: CYCLE & VALUE SCREENER (NEW)
# ==========================================
elif app_mode == "🔮 Cycle & Value Screener":
    st.title("🔮 Cycle & Value Screener")
    st.write("Enter an asset below to calculate its mathematical probability of being at a cycle high or low.")
    
    scan_ticker = st.text_input("Asset to Analyze (e.g., INFY.NS, ETH-USD):").upper()
    
    if scan_ticker:
        with st.spinner(f"Running mathematical analysis on {scan_ticker}..."):
            try:
                # 1. Fetch 6 months of data
                data = yf.Ticker(scan_ticker).history(period="6mo")
                
                if not data.empty:
                    close = data['Close']
                    current_price = close.iloc[-1]
                    
                    # 2. Calculate RSI (Relative Strength Index)
                    delta = close.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    current_rsi = rsi.iloc[-1]
                    
                    # 3. Calculate Bollinger Bands (Standard Deviations)
                    sma_20 = close.rolling(window=20).mean()
                    std_20 = close.rolling(window=20).std()
                    lower_band = sma_20 - (2 * std_20)
                    upper_band = sma_20 + (2 * std_20)
                    
                    c_lower = lower_band.iloc[-1]
                    c_upper = upper_band.iloc[-1]
                    c_sma = sma_20.iloc[-1]
                    
                    # 4. Generate the Logic/Recommendation
                    st.header(f"Analysis for {scan_ticker}")
                    st.write(f"**Current Price:** ₹{current_price:,.2f}")
                    st.divider()
                    
                    col1, col2 = st.columns(2)
                    
                    # RSI Display
                    with col1:
                        st.subheader("Momentum (RSI 14)")
                        st.metric("RSI Score (0-100)", f"{current_rsi:.1f}")
                        if current_rsi < 30:
                            st.success("🟢 Probability: OVERSOLD. The asset has dropped significantly and is historically due for a bounce.")
                        elif current_rsi > 70:
                            st.error("🔴 Probability: OVERBOUGHT. The asset has run up too fast and is historically due for a pullback.")
                        else:
                            st.info("🟡 Probability: NEUTRAL. The asset is moving at a normal, sustainable pace.")
                            
                    # Bollinger Bands Display
                    with col2:
                        st.subheader("Mean Reversion (Bollinger)")
                        st.write(f"**Average Price (20-day):** ₹{c_sma:,.2f}")
                        if current_price <= c_lower * 1.02: # Within 2% of bottom band
                            st.success(f"🟢 Signal: AT CYCLE LOW. Price is hitting the statistical floor (₹{c_lower:,.2f}). Excellent buy zone.")
                        elif current_price >= c_upper * 0.98: # Within 2% of top band
                            st.error(f"🔴 Signal: AT CYCLE HIGH. Price is hitting the statistical ceiling (₹{c_upper:,.2f}). High risk buy zone.")
                        else:
                            st.info("🟡 Signal: MID-CYCLE. Price is floating between the historical floor and ceiling.")
                            
                    # Chart
                    st.divider()
                    st.subheader("6-Month Price Action")
                    st.line_chart(close)
                else:
                    st.error("No data found.")
            except Exception as e:
                st.error(f"Error calculating stats: {e}")
