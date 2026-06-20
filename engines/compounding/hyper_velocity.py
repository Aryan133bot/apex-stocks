import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def get_universe():
    universe_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'universe.txt')
    with open(universe_path, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers

def fetch_data(tickers):
    print(f"1. Fetching 1-Year Historical Data for {len(tickers)} Stocks...")
    stock_data = {}
    for ticker in tickers:
        df = yf.download(ticker, period="1y", progress=False)
        if df.empty: continue
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if len(df) < 130: continue
            
        df['Vol_20D'] = df['Volume'].rolling(20).mean()
        df['Vol_5D'] = df['Volume'].rolling(5).mean()
        df['High_52W'] = df['High'].rolling(120).max() # Using 6-month high for more signals
        df['Low_52W'] = df['Low'].rolling(120).min()
        df['Price_Move'] = np.where(df['Open'] > 0, ((df['Close'] - df['Open']) / df['Open']) * 100, 0)
        
        # Momentum Breakout Gate
        df['Is_Breakout'] = (df['Close'] >= df['High_52W'] * 0.95) & (df['Vol_5D'] > 1.2 * df['Vol_20D']) & (df['Close'] > 50)
        
        # Velocity Score: Ranks the strongest breakout of the day
        # Score = % Distance from Low + % Volume Spike
        dist_pct = ((df['Close'] - df['Low_52W']) / df['Low_52W']) * 100
        vol_spike = (df['Vol_5D'] / df['Vol_20D']) * 100
        df['Velocity_Score'] = dist_pct + vol_spike
        
        stock_data[ticker] = df
    return stock_data

def run_10k_challenge():
    print("=== APEX HYPER-VELOCITY COMPOUNDING (Rs.10k CHALLENGE) ===")
    tickers = get_universe()
    stock_data = fetch_data(tickers)
    
    # Use Reliance to build the master date index
    if "RELIANCE.NS" in stock_data:
        master_dates = stock_data["RELIANCE.NS"].index
    else:
        master_dates = list(stock_data.values())[0].index
        
    # Simulate past 6 months (approx 125 trading days)
    sim_dates = master_dates[-125:]
    
    capital = 10000.0
    position = None # None means we are in cash
    
    trade_log = []
    
    print("\n2. Executing High-Frequency Simulation (Past 6 Months)...")
    
    for i, current_date in enumerate(sim_dates):
        # 1. Manage Active Position
        if position is not None:
            ticker = position['ticker']
            df = stock_data[ticker]
            
            # Check if current_date is in df
            if current_date not in df.index:
                continue
                
            today_row = df.loc[current_date]
            today_low = float(today_row['Low'])
            today_close = float(today_row['Close'])
            
            position['days_held'] += 1
            
            # Update Trailing Stop Loss (Peak - 6%)
            peak = max(position['peak_price'], float(today_row['High']))
            position['peak_price'] = peak
            trailing_stop = peak * 0.94 # 6% trailing stop
            
            # Check Exits
            sell_price = None
            sell_reason = ""
            
            if today_low <= trailing_stop:
                sell_price = trailing_stop
                sell_reason = "TRAILING STOP (-6%)"
                
            if sell_price is not None:
                # Liquidate and Reinvest
                shares = position['shares']
                pnl = (sell_price - position['entry_price']) * shares
                capital += pnl
                
                trade_log.append({
                    "ticker": ticker,
                    "entry_date": position['entry_date'].strftime('%Y-%m-%d'),
                    "exit_date": current_date.strftime('%Y-%m-%d'),
                    "pnl_pct": ((sell_price - position['entry_price']) / position['entry_price']) * 100.0,
                    "profit": pnl,
                    "capital_after": capital,
                    "reason": sell_reason
                })
                position = None # Back to cash
                
        # 2. Look for New Entry (If in Cash)
        if position is None and i < len(sim_dates) - 1:
            # Rank all stocks for today
            candidates = []
            for ticker, df in stock_data.items():
                if current_date in df.index:
                    row = df.loc[current_date]
                    if bool(row['Is_Breakout']):
                        candidates.append((ticker, float(row['Velocity_Score'])))
                        
            if candidates:
                # Sort by Velocity Score descending
                candidates.sort(key=lambda x: x[1], reverse=True)
                top_ticker = candidates[0][0] # The absolute #1 strongest stock today
                
                # Enter at T+1 Open
                next_date = sim_dates[i+1]
                if next_date in stock_data[top_ticker].index:
                    entry_price = float(stock_data[top_ticker].loc[next_date]['Open'])
                    if entry_price > 0:
                        shares = capital / entry_price
                        position = {
                            "ticker": top_ticker,
                            "entry_date": next_date,
                            "entry_price": entry_price,
                            "shares": shares,
                            "peak_price": entry_price,
                            "days_held": 0
                        }

    # Close out any remaining position on the last day
    if position is not None:
        last_date = sim_dates[-1]
        ticker = position['ticker']
        if last_date in stock_data[ticker].index:
            sell_price = float(stock_data[ticker].loc[last_date]['Close'])
            pnl = (sell_price - position['entry_price']) * position['shares']
            capital += pnl
            trade_log.append({
                "ticker": ticker,
                "entry_date": position['entry_date'].strftime('%Y-%m-%d'),
                "exit_date": last_date.strftime('%Y-%m-%d'),
                "pnl_pct": ((sell_price - position['entry_price']) / position['entry_price']) * 100.0,
                "profit": pnl,
                "capital_after": capital,
                "reason": "END OF SIMULATION"
            })
            
    # Print Results
    print("\n" + "="*85)
    print(f"{'Entry Date':<12} | {'Exit Date':<12} | {'Ticker':<12} | {'PnL %':<8} | {'Profit':<8} | {'Capital':<10} | {'Reason'}")
    print("="*85)
    for t in trade_log:
        pnl_str = f"{t['pnl_pct']:+.1f}%"
        prof_str = f"Rs.{t['profit']:+.0f}"
        cap_str = f"Rs.{t['capital_after']:.0f}"
        print(f"{t['entry_date']:<12} | {t['exit_date']:<12} | {t['ticker']:<12} | {pnl_str:<8} | {prof_str:<8} | {cap_str:<10} | {t['reason']}")
        
    print("\n" + "="*50)
    print("Rs.10k COMPOUNDING SUMMARY (6 MONTHS)")
    print("="*50)
    print(f"Total Trades     : {len(trade_log)}")
    wins = len([t for t in trade_log if t['pnl_pct'] > 0])
    win_rate = (wins / len(trade_log)) * 100 if trade_log else 0
    print(f"Win Rate         : {win_rate:.1f}%")
    print(f"Starting Capital : Rs.10,000")
    print(f"Final Capital    : Rs.{capital:.2f}")
    print(f"Net Profit       : Rs.{capital - 10000:.2f} ({((capital - 10000)/10000)*100:.1f}%)")
    print("="*50)

if __name__ == "__main__":
    run_10k_challenge()
