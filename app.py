import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

st.set_page_config(page_title="Paper Trader Pro", layout="wide")

# --- 1. CACHING THE PRICE ---
@st.cache_data(ttl=60, show_spinner=False)
def get_live_price(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        if hist.empty:
            return None
        return float(hist['Close'].iloc[-1])
    except:
        return None

# --- 2. DATA SAVING & LOADING SYSTEM ---
DATA_FILE = "trading_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data["cash"], pd.DataFrame(data["portfolio"])
    else:
        return 100000.00, pd.DataFrame(columns=["Ticker", "Shares", "Total Invested"])

def save_data(cash, portfolio_df):
    data = {
        "cash": cash,
        "portfolio": portfolio_df.to_dict("records")
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

if "cash" not in st.session_state:
    st.session_state.cash, st.session_state.portfolio = load_data()


# --- SIDEBAR SETTINGS (RESET BUTTON) ---
with st.sidebar:
    st.header("⚙️ Account Settings")
    st.write("Use this to wipe your data and start fresh.")
    
    if st.button("🚨 Reset Account (₹1,00,00,000)"):
        st.session_state.cash = 10000000.00
        st.session_state.portfolio = pd.DataFrame(columns=["Ticker", "Shares", "Total Invested"])
        save_data(st.session_state.cash, st.session_state.portfolio)
        st.cache_data.clear()
        st.success("Account successfully reset!")
        st.rerun()


# --- 3. LIVE PORTFOLIO CALCULATIONS ---
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

# --- 4. TOP DASHBOARD ---
col1, col2, col3 = st.columns(3)
col1.metric("Virtual Cash Available", f"₹{st.session_state.cash:,.2f}")
col2.metric("Total Asset Value", f"₹{total_stock_value:,.2f}")
col3.metric("Total Account Value", f"₹{(st.session_state.cash + total_stock_value):,.2f}")

st.divider()

# --- 5. TRADING TERMINAL (BUY & SELL TABS) ---
st.header("Trading Terminal")
tab1, tab2 = st.tabs(["🟢 Buy", "🔴 Sell"])

with tab1: # BUY LOGIC
    buy_ticker = st.text_input("Ticker to Buy (e.g., RELIANCE.NS, BTC-USD):", key="buy_ticker").upper()
    if buy_ticker:
        current_price = get_live_price(buy_ticker)
        
        if current_price is None:
            st.error(f"⚠️ No market data found for '{buy_ticker}'. Check spelling, or ensure Indian stocks end in .NS")
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
                    
                    # BUG FIX: Removed the line that caused the crash here!
                    
                    st.success(f"Trade Executed! Bought {shares_to_buy} of {buy_ticker}.")
                    st.rerun()

with tab2: # SELL LOGIC
    if not st.session_state.portfolio.empty:
        owned_tickers = st.session_state.portfolio['Ticker'].tolist()
        sell_ticker = st.selectbox("Ticker to Sell:", owned_tickers)
        
        idx = st.session_state.portfolio.index[st.session_state.portfolio['Ticker'] == sell_ticker][0]
        owned_shares = float(st.session_state.portfolio.at[idx, 'Shares'])
        total_invested = float(st.session_state.portfolio.at[idx, 'Total Invested'])
        
        st.info(f"You currently own **{owned_shares:.4f}** of {sell_ticker}.")
        
        current_price = get_live_price(sell_ticker)
        
        if current_price is None:
             st.error("Could not fetch live price right now. Try again in a moment.")
        else:
            st.success(f"Current Market Price: **₹{current_price:,.2f}**")
            
            shares_to_sell = st.number_input(f"Amount to Sell", min_value=0.01, max_value=owned_shares, step=1.0)
            proceeds = shares_to_sell * current_price
            st.write(f"**Estimated Proceeds:** ₹{proceeds:,.2f}")
            
            if st.button("Execute Sell"):
                st.session_state.cash += proceeds
                avg_cost_per_share = total_invested / owned_shares
                cost_of_sold_shares = avg_cost_per_share * shares_to_sell
                
                st.session_state.portfolio.at[idx, 'Shares'] -= shares_to_sell
                st.session_state.portfolio.at[idx, 'Total Invested'] -= cost_of_sold_shares
                
                if st.session_state.portfolio.at[idx, 'Shares'] <= 0.0001:
                    st.session_state.portfolio = st.session_state.portfolio.drop(idx).reset_index(drop=True)
                
                save_data(st.session_state.cash, st.session_state.portfolio)
                st.success(f"Sold {shares_to_sell} of {sell_ticker}!")
                st.rerun()
    else:
        st.info("You don't own any assets to sell yet.")

st.divider()

# --- 6. VIEW LIVE PORTFOLIO ---
st.header("My Open Positions (Live)")
if not live_portfolio.empty:
    formatted_portfolio = live_portfolio.style.format({
        "Shares": "{:.4f}",
        "Total Invested": "₹{:,.2f}",
        "Live Price": "₹{:,.2f}",
        "Avg Buy Price": "₹{:,.2f}",
        "Current Value": "₹{:,.2f}",
        "Profit/Loss (₹)": "₹{:,.2f}",
        "Profit/Loss (%)": "{:,.2f}%"
    })
    
    st.dataframe(formatted_portfolio, use_container_width=True, hide_index=True)
else:
    st.info("Your portfolio is empty. Head to the Buy tab to make your first trade!")