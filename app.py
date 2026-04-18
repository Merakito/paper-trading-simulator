import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import random

st.set_page_config(page_title="Paper Trader Pro", layout="wide")

# --- 1. CORE FUNCTIONS & CACHING ---
@st.cache_data(ttl=60, show_spinner=False)
def get_live_price(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        if hist.empty:
            return None
        return float(hist['Close'].iloc[-1])
    except:
        return None

DATA_FILE = "trading_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            df = pd.DataFrame(data["portfolio"])
            if df.empty or "Ticker" not in df.columns:
                df = pd.DataFrame(columns=["Ticker", "Shares", "Total Invested"])
            return data["cash"], df
    else:
        return 10000000.00, pd.DataFrame(columns=["Ticker", "Shares", "Total Invested"])

def save_data(cash, portfolio_df):
    data = {"cash": cash, "portfolio": portfolio_df.to_dict("records")}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Initialize Live Trading State
if "cash" not in st.session_state:
    st.session_state.cash, st.session_state.portfolio = load_data()

# Initialize Game State
if "game_step" not in st.session_state:
    st.session_state.game_step = "generate" 
    st.session_state.score = 0
    st.session_state.streak = 0
    st.session_state.g_ticker = ""
    st.session_state.g_visible = pd.Series()
    st.session_state.g_hidden = pd.Series()
    st.session_state.g_full = pd.Series()
    st.session_state.g_result_msg = ""


# --- 2. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Navigation")
    app_mode = st.radio("Choose Mode:", ["📈 Live Trading", "🎮 Market Replay Academy"])
    
    st.divider()
    st.header("⚙️ Settings")
    if st.button("🚨 Reset Live Account (₹1 Crore)"):
        st.session_state.cash = 10000000.00
        st.session_state.portfolio = pd.DataFrame(columns=["Ticker", "Shares", "Total Invested"])
        save_data(st.session_state.cash, st.session_state.portfolio)
        st.cache_data.clear()
        st.success("Account reset to ₹1 Crore!")
        st.rerun()


# ==========================================
# MODE 1: LIVE TRADING SIMULATOR
# ==========================================
if app_mode == "📈 Live Trading":
    st.title("📈 My Paper Trading Simulator")

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
            live_portfolio['Avg Buy Price'] = live_portfolio['Total Invested'] / live_portfolio['Shares']
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
                shares_to_buy = st.number_input(f"Shares/Coins to Buy", min_value=0.01, step=1.0, key="buy_shares")
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
                        save_data(st.session_state.cash, st.session_state.portfolio)
                        st.success(f"Trade Executed! Bought {shares_to_buy} of {buy_ticker}.")
                        st.rerun()

    with tab2: 
        if not st.session_state.portfolio.empty:
            owned_tickers = st.session_state.portfolio['Ticker'].tolist()
            sell_ticker = st.selectbox("Ticker to Sell:", owned_tickers)
            idx = st.session_state.portfolio.index[st.session_state.portfolio['Ticker'] == sell_ticker][0]
            owned_shares = float(st.session_state.portfolio.at[idx, 'Shares'])
            total_invested = float(st.session_state.portfolio.at[idx, 'Total Invested'])
            
            st.info(f"You own **{owned_shares:.4f}** of {sell_ticker}.")
            current_price = get_live_price(sell_ticker)
            
            if current_price is None:
                 st.error("Could not fetch live price right now.")
            else:
                st.success(f"Current Market Price: **₹{current_price:,.2f}**")
                shares_to_sell = st.number_input(f"Amount to Sell", min_value=0.01, max_value=owned_shares, step=1.0)
                proceeds = shares_to_sell * current_price
                st.write(f"**Estimated Proceeds:** ₹{proceeds:,.2f}")
                
                if st.button("Execute Sell"):
                    st.session_state.cash += proceeds
                    avg_cost = total_invested / owned_shares
                    st.session_state.portfolio.at[idx, 'Shares'] -= shares_to_sell
                    st.session_state.portfolio.at[idx, 'Total Invested'] -= (avg_cost * shares_to_sell)
                    if st.session_state.portfolio.at[idx, 'Shares'] <= 0.0001:
                        st.session_state.portfolio = st.session_state.portfolio.drop(idx).reset_index(drop=True)
                    save_data(st.session_state.cash, st.session_state.portfolio)
                    st.success(f"Sold {shares_to_sell} of {sell_ticker}!")
                    st.rerun()
        else:
            st.info("You don't own any assets to sell yet.")

    st.divider()
    st.header("My Open Positions (Live)")
    if not live_portfolio.empty:
        formatted_portfolio = live_portfolio.style.format({
            "Shares": "{:.4f}", "Total Invested": "₹{:,.2f}", "Live Price": "₹{:,.2f}",
            "Avg Buy Price": "₹{:,.2f}", "Current Value": "₹{:,.2f}",
            "Profit/Loss (₹)": "₹{:,.2f}", "Profit/Loss (%)": "{:,.2f}%"
        })
        st.dataframe(formatted_portfolio, use_container_width=True, hide_index=True)
    else:
        st.info("Your portfolio is empty.")


# ==========================================
# MODE 2: MARKET REPLAY ACADEMY (THE GAME)
# ==========================================
elif app_mode == "🎮 Market Replay Academy":
    st.title("🎮 Market Replay Academy")
    st.write("Test your pattern recognition. I'll show you the past; you predict the future.")
    
    # Game Helper Functions
    def generate_scenario():
        tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "RELIANCE.NS", "TATASTEEL.NS"]
        ticker = random.choice(tickers)
        year = random.randint(2018, 2023)
        month = random.randint(1, 10)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month+2:02d}-28"
        
        try:
            hist = yf.Ticker(ticker).history(start=start_date, end=end_date)
            if len(hist) > 50:
                closes = hist['Close']
                split = int(len(closes) * 0.7) # Show 70%, hide 30%
                st.session_state.g_visible = closes.iloc[:split]
                st.session_state.g_hidden = closes.iloc[split:]
                st.session_state.g_full = closes
                st.session_state.g_ticker = ticker
                st.session_state.game_step = "guessing"
            else:
                generate_scenario() # Try again if data is bad
        except:
            generate_scenario()

    def check_guess(guess):
        start_price = st.session_state.g_visible.iloc[-1]
        end_price = st.session_state.g_hidden.iloc[-1]
        went_up = end_price > start_price
        
        if (guess == "UP" and went_up) or (guess == "DOWN" and not went_up):
            st.session_state.score += 500
            st.session_state.streak += 1
            st.session_state.g_result_msg = f"✅ **CORRECT!** The price went from {start_price:.2f} to {end_price:.2f}."
        else:
            st.session_state.score -= 250
            st.session_state.streak = 0
            st.session_state.g_result_msg = f"❌ **WRONG!** The price went from {start_price:.2f} to {end_price:.2f}. You got trapped!"
        
        st.session_state.game_step = "revealed"
        st.rerun()

    # Top Scoreboard
    g_col1, g_col2 = st.columns(2)
    g_col1.metric("Academy Score", st.session_state.score)
    g_col2.metric("Winning Streak", f"{st.session_state.streak} 🔥")
    st.divider()

    # State Machine
    if st.session_state.game_step == "generate":
        with st.spinner("Finding a random historical setup..."):
            generate_scenario()
            st.rerun()

    elif st.session_state.game_step == "guessing":
        st.subheader("Asset: Hidden (Crypto or Indian Stock)")
        st.write("Based on this trend, what happens next?")
        st.line_chart(st.session_state.g_visible)
        
        col_up, col_down = st.columns(2)
        if col_up.button("📈 PREDICT: BREAKOUT (UP)", use_container_width=True):
            check_guess("UP")
        if col_down.button("📉 PREDICT: CRASH (DOWN)", use_container_width=True):
            check_guess("DOWN")

    elif st.session_state.game_step == "revealed":
        st.subheader(f"Asset Revealed: {st.session_state.g_ticker}")
        st.line_chart(st.session_state.g_full)
        
        if "CORRECT" in st.session_state.g_result_msg:
            st.success(st.session_state.g_result_msg)
        else:
            st.error(st.session_state.g_result_msg)
            
        if st.button("Play Next Scenario ➡️", use_container_width=True):
            st.session_state.game_step = "generate"
            st.rerun()
