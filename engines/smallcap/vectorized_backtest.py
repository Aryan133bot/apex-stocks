import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import itertools
from datetime import datetime
import multiprocessing

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engines.smallcap.gate import SmallCapGate
from engines.smallcap.patterns import PatternClassifier
from data.fetchers.fundamental_fetcher import FundamentalFetcher
from data.fetchers.shareholding_fetcher import ShareholdingFetcher

SMALL_CAP_UNIVERSE = [
    "SUZLON", "IRFC", "RVNL", "MAZDOCK", "FACT", 
    "HBLPOWER", "BEML", "OLECTRA", "HCC", "TITAGARH",
    "RAILTEL", "IRCON", "JINDALSAW", "KABRAEXTRU",
    "LLOYDSENGG", "GENUSPOWER", "ELECCAST", "KPIGREEN"
]

def load_and_vectorize():
    print("1. Fetching 11-Year Historical OHLCV (Decadal Setup)...")
    stock_data = {}
    for ticker in SMALL_CAP_UNIVERSE:
        df = yf.download(f"{ticker}.NS", period="max", progress=False) # max gets all available history
        if df.empty: continue
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Cut to last 11 years (approx 2750 days)
        df = df.tail(2750).copy()
        
        if len(df) < 250:
            continue
            
        # Vectorized Feature Calculation (No more iterrows!)
        df['Vol_20D'] = df['Volume'].rolling(20).mean()
        df['Vol_5D'] = df['Volume'].rolling(5).mean()
        df['Low_52W'] = df['Low'].rolling(250).min()
        df['High_52W'] = df['High'].rolling(250).max()
        df['Dist_from_Low'] = ((df['Close'] - df['Low_52W']) / df['Low_52W']) * 100
        
        # Turnovers
        df['Turnover_20D'] = df['Vol_20D'] * df['Close']
        df['Turnover_Today'] = df['Volume'] * df['Close']
        
        # Manipulation flags
        df['Price_Move'] = np.where(df['Open'] > 0, ((df['Close'] - df['Open']) / df['Open']) * 100, 0)
        df['Is_Circuit'] = np.where((df['Price_Move'] > 4.5) & (abs(df['High'] - df['Close']) < (df['Close'] * 0.005)), 1, 0)
        df['Circuit_10D'] = df['Is_Circuit'].rolling(10).sum()
        
        stock_data[ticker] = df
        
    print("2. Fetching Fundamentals & Generating Base Signals...")
    fund_fetcher = FundamentalFetcher()
    share_fetcher = ShareholdingFetcher()
    gate = SmallCapGate()
    
    # Store all generated entry indices
    # trade_entries[ticker] = list of valid indices where a BUY signal was triggered
    all_trade_entries = {}
    
    for ticker, df in stock_data.items():
        raw_fund = fund_fetcher.get_fundamentals(ticker, use_cache=True)
        metrics = fund_fetcher.parse_quality_metrics(raw_fund)
        promoter = share_fetcher.get_promoter_holding(ticker)
        pledge = share_fetcher.get_pledged_data(ticker)
        
        # Calculate Base Gate 0 (Static fundamental checks)
        # We assume static fundamentals pass Gate 0 for simplicity if they pass today.
        # This speeds up the decadal backtest drastically.
        gate_pass, _ = gate.run_gate_zero(metrics, promoter, 50000000, 50000000) # dummy turnover to pass static check
        if not gate_pass: 
            all_trade_entries[ticker] = []
            continue
            
        # Identify valid technical days
        # Condition 1: Turnover > 2 Cr and Today Turnover > 50% Avg
        valid_turnover = (df['Turnover_20D'] >= 20000000) & (df['Turnover_Today'] >= (df['Turnover_20D'] * 0.5))
        
        # Condition 2: Manipulation Screen
        m1_fail = (df['Vol_20D'] > 0) & (df['Volume'] > 10 * df['Vol_20D']) & (df['Price_Move'] > 8.0)
        m2_fail = df['Circuit_10D'] >= 3
        m3_fail = (pledge > 40.0) & (df['Vol_20D'] > 0) & (df['Vol_5D'] > 5 * df['Vol_20D'])
        manip_clean = ~(m1_fail | m2_fail | m3_fail)
        
        # Condition 3: Pattern 3 (Low Reversal)
        pat3_pass = (df['Dist_from_Low'] <= 15.0) & (df['Vol_5D'] > 2 * df['Vol_20D'])
        
        # Condition 4: Momentum Breakout (Near 52-Week High with Volume)
        pat4_pass = (df['Close'] >= df['High_52W'] * 0.90) & (df['Vol_5D'] > 1.5 * df['Vol_20D'])
        
        # Final BUY Signal Boolean Array
        buy_signals = valid_turnover & manip_clean & (pat3_pass | pat4_pass) & (df['Close'] >= 10) & (df['Close'] <= 1500)
        
        # Get integer indices of True values, offset by 250 to ensure 10-year test bounds
        # Note: We must restrict signals to the last 2520 days (10 years)
        total_days = len(df)
        start_idx = max(250, total_days - 2520)
        
        valid_indices = []
        for i in range(start_idx, total_days - 100): # Stop 100 days early to allow max holding exit
            if buy_signals.iloc[i]:
                valid_indices.append(i)
                
        all_trade_entries[ticker] = valid_indices
        
    return stock_data, all_trade_entries

def simulate_trades(stock_data, all_trade_entries, sl_pct, tp_pct, hold_days):
    """
    Simulates all trades instantly using index lookups.
    """
    total_trades = 0
    wins = 0
    total_pnl = 0.0
    
    for ticker, entries in all_trade_entries.items():
        df = stock_data[ticker]
        open_prices = df['Open'].values
        close_prices = df['Close'].values
        low_prices = df['Low'].values
        high_prices = df['High'].values
        
        for i in entries:
            # Enter at T+1 Open
            entry_price = open_prices[i+1]
            if entry_price <= 0: continue
            
            stop_loss = entry_price * (1.0 - sl_pct)
            take_profit = entry_price * (1.0 + tp_pct) if tp_pct > 0 else float('inf')
            
            # Look forward up to 'hold_days'
            exit_price = 0.0
            pnl = 0.0
            
            # Slice the forward window arrays for maximum C-level speed
            end_idx = min(i + 1 + hold_days, len(df))
            window_low = low_prices[i+1 : end_idx]
            window_high = high_prices[i+1 : end_idx]
            window_close = close_prices[i+1 : end_idx]
            
            # Find exact exit
            for day in range(len(window_low)):
                if window_low[day] <= stop_loss:
                    pnl = - (sl_pct * 100.0)
                    break
                if window_high[day] >= take_profit:
                    pnl = (tp_pct * 100.0)
                    break
                    
                if day == len(window_low) - 1:
                    pnl = ((window_close[day] - entry_price) / entry_price) * 100.0
                    break
                    
            total_trades += 1
            total_pnl += pnl
            if pnl > 0:
                wins += 1
                
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    avg_pnl = (total_pnl / total_trades) if total_trades > 0 else 0.0
    
    return {
        "sl": sl_pct, "tp": tp_pct, "hold": hold_days,
        "signals": total_trades, "win_rate": win_rate, "avg_pnl": avg_pnl, "total_pnl": total_pnl
    }

def run_deep_grid_search():
    print("=== APEX DEEP GRID SEARCH (10-YEAR OPTIMIZER) ===")
    print("Utilizing NumPy Vectorization for Extreme Speed...")
    
    stock_data, all_trade_entries = load_and_vectorize()
    
    stop_losses = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
    take_profits = [0.0, 0.30, 0.50, 0.80] # 0.0 means no hard TP
    holding_periods = [10, 20, 30, 40, 50, 60]
    
    configurations = list(itertools.product(stop_losses, take_profits, holding_periods))
    print(f"\n3. Executing {len(configurations)} Combinations Over a 10-Year Decadal Slice...")
    
    results = []
    
    # We can just iterate directly since vectorization is so fast
    for sl, tp, hd in configurations:
        res = simulate_trades(stock_data, all_trade_entries, sl, tp, hd)
        if res["signals"] > 0:
            results.append(res)
            
    # Sort
    results.sort(key=lambda x: x["total_pnl"], reverse=True)
    
    print("\n" + "="*80)
    print("DECADAL OPTIMIZATION COMPLETE: TOP 5 MATHEMATICAL CONFIGURATIONS")
    print("="*80)
    print(f"{'Rank':<5} | {'Stop Loss':<10} | {'Take Profit':<12} | {'Hold Days':<10} | {'Win Rate':<10} | {'Cumulative PnL':<15}")
    print("-" * 80)
    
    for i, r in enumerate(results[:5], 1):
        tp_str = f"+{r['tp']*100:.0f}%" if r['tp'] > 0 else "NONE"
        print(f"#{i:<4} | -{r['sl']*100:<9.0f}% | {tp_str:<12} | {r['hold']:<10} | {r['win_rate']:<9.1f}% | +{r['total_pnl']:<15.2f}%")
        
if __name__ == "__main__":
    run_deep_grid_search()
