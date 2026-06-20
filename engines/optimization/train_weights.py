import os
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engines.bull.relative_strength import RelativeStrengthEngine
from engines.bull.momentum import MomentumBullEngine
from core.types import DataPacket, Signal, SignalCategory, SignalSubSource

def run_grid_search():
    print("=== 20-YEAR ALGORITHMIC WEIGHT GRID SEARCH ===")
    
    stocks = ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "LT.NS", "ITC.NS", "SBIN.NS", "TCS.NS", "BHARTIARTL.NS"]
    print("Downloading 20 years of massive Nifty heavyweight data...")
    
    nifty = yf.download("^NSEI", start="2006-01-01", end="2026-06-05", progress=False)['Close']
    if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
    
    stock_data = {}
    for t in stocks:
        df = yf.download(t, start="2006-01-01", end="2026-06-05", progress=False)['Close']
        if isinstance(df, pd.DataFrame): df = df.iloc[:, 0]
        stock_data[t] = df
        
    sample_dates = pd.date_range(start="2008-01-01", end="2025-06-01", freq="6MS")
    
    print(f"Executing Grid Search across {len(sample_dates)} unique 6-month historical epochs...\n")
    
    combinations = [
        (0.1, 0.9), (0.2, 0.8), (0.3, 0.7), (0.4, 0.6), (0.5, 0.5),
        (0.6, 0.4), (0.7, 0.3), (0.8, 0.2), (0.9, 0.1)
    ]
    
    results = {comb: [] for comb in combinations}
    
    for date in sample_dates:
        target_date = date.strftime("%Y-%m-%d")
        
        for ticker in stocks:
            series = stock_data[ticker]
            hist_data = series[series.index <= target_date]
            if len(hist_data) < 200: continue
            
            nifty_hist = nifty[nifty.index <= target_date]
            if len(nifty_hist) < 200: continue
            
            current_price = hist_data.iloc[-1]
            stock_63d_ret = (current_price / hist_data.iloc[-63]) - 1
            nifty_63d_ret = (nifty_hist.iloc[-1] / nifty_hist.iloc[-63]) - 1
            
            future_data = series[series.index > target_date]
            if len(future_data) < 120: continue 
            forward_6m_return = (future_data.iloc[120] / current_price) - 1
            
            packet = DataPacket(ticker=ticker, timestamp=datetime.utcnow())
            packet.signals.append(Signal("STOCK_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, stock_63d_ret, datetime.utcnow()))
            packet.signals.append(Signal("NIFTY_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, nifty_63d_ret, datetime.utcnow()))
            packet.signals.append(Signal("SECTOR_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, nifty_63d_ret, datetime.utcnow()))
            
            rs_score = RelativeStrengthEngine().evaluate(packet)['score']
            mom_score = MomentumBullEngine().evaluate(packet)['score']
            
            for (w_rs, w_mom) in combinations:
                weighted_score = (rs_score * w_rs) + (mom_score * w_mom)
                if weighted_score > 60.0:
                    results[(w_rs, w_mom)].append(forward_6m_return)
                    
    print("==============================================")
    print("=== GRID SEARCH ACCURACY REPORT ===")
    best_weight = None
    best_ret = -999
    
    for (w_rs, w_mom), returns in results.items():
        if len(returns) == 0: continue
        avg_ret = np.mean(returns) * 100
        win_rate = (len([r for r in returns if r > 0]) / len(returns)) * 100
        print(f"Weights [RS: {int(w_rs*100):2d}% | Mom: {int(w_mom*100):2d}%] -> Win Rate: {win_rate:5.1f}% | Avg 6M Return: {avg_ret:5.2f}%")
        
        if avg_ret > best_ret:
            best_ret = avg_ret
            best_weight = (w_rs, w_mom)
            
    print("==============================================")
    print(f"=> OPTIMAL 20-YEAR ALGORITHMIC WEIGHTS: Relative Strength = {int(best_weight[0]*100)}% | Momentum = {int(best_weight[1]*100)}%")
    print("==============================================")

if __name__ == "__main__":
    run_grid_search()
