import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engines.smallcap.vectorized_backtest import load_and_vectorize

def simulate_past_month():
    print("=== APEX Rs.10,000 REAL-WORLD SIMULATION (PAST 30 DAYS) ===")
    
    # 1. Fetch data and generate all signals using the vectorized backend
    stock_data, all_trade_entries = load_and_vectorize()
    
    print("\nExtracting trades from the last 21 trading days (approx 1 month)...")
    
    # Identify the index for the last 21 days
    # Using SUZLON as the base clock
    base_df = stock_data["SUZLON"]
    total_days = len(base_df)
    past_month_start_idx = total_days - 21
    
    active_trades = []
    
    for ticker, entries in all_trade_entries.items():
        df = stock_data[ticker]
        for idx in entries:
            # Check if the signal happened in the last 21 trading days
            if idx >= past_month_start_idx and idx < total_days - 1:
                signal_date = df.index[idx].strftime('%Y-%m-%d')
                entry_date = df.index[idx + 1].strftime('%Y-%m-%d')
                entry_price = float(df['Open'].iloc[idx + 1])
                
                # Check performance up to TODAY (the last row in the dataframe)
                current_price = float(df['Close'].iloc[-1])
                
                # Check if it hit the optimal -20% stop loss at any point
                window_lows = df['Low'].iloc[idx + 1:]
                stop_loss_price = entry_price * 0.80
                
                status = "OPEN"
                exit_price = current_price
                
                for low in window_lows:
                    if low <= stop_loss_price:
                        status = "STOPPED OUT"
                        exit_price = stop_loss_price
                        break
                        
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0
                
                active_trades.append({
                    "ticker": ticker,
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "current_price": exit_price,
                    "status": status,
                    "pnl_pct": pnl_pct
                })
                
    if not active_trades:
        print("\nThe system was heavily defensive and generated 0 trades in the past month.")
        return
        
    print("-" * 75)
    print(f"{'Ticker':<12} | {'Entry Date':<12} | {'Entry (Rs.)':<11} | {'Current (Rs.)':<13} | {'Status':<12} | {'PnL %':<10}")
    print("-" * 75)
    
    for t in active_trades:
        print(f"{t['ticker']:<12} | {t['entry_date']:<12} | {t['entry_price']:<11.2f} | {t['current_price']:<13.2f} | {t['status']:<12} | {t['pnl_pct']:<10.2f}%")
        
    # Calculate Rs.10,000 Portfolio Allocation
    initial_capital = 10000.0
    allocation_per_trade = initial_capital / len(active_trades)
    
    total_current_value = 0.0
    
    for t in active_trades:
        multiplier = 1.0 + (t['pnl_pct'] / 100.0)
        final_value = allocation_per_trade * multiplier
        total_current_value += final_value
        
    net_profit_rupees = total_current_value - initial_capital
    net_profit_pct = (net_profit_rupees / initial_capital) * 100.0
    
    print("\n" + "="*50)
    print("PORTFOLIO PERFORMANCE (1-MONTH HYPOTHETICAL)")
    print("="*50)
    print(f"Initial Investment : Rs.10,000.00")
    print(f"Capital Deployed   : Rs.{allocation_per_trade:.2f} across {len(active_trades)} trades")
    print(f"Current Value      : Rs.{total_current_value:.2f}")
    print(f"Net Profit/Loss    : Rs.{net_profit_rupees:.2f} ({net_profit_pct:+.2f}%)")
    print("="*50)

if __name__ == "__main__":
    simulate_past_month()
