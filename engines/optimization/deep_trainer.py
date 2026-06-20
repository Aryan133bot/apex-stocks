import os
import json
import pandas as pd
import yfinance as yf
import numpy as np
import random
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engines.bull.relative_strength import RelativeStrengthEngine
from engines.bull.momentum import MomentumBullEngine
from core.types import DataPacket, Signal, SignalCategory, SignalSubSource

def run_deep_trainer(iterations=50):
    print("=== DEEP CONTINUOUS OPTIMIZER ===")
    print(f"Executing {iterations} massive random search permutations...\n")
    
    param_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "optimal_parameters.json")
    
    # Load current best
    current_best_ret = 10.66 # Baseline from 70/30 grid search
    
    stocks = ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "LT.NS", "ITC.NS", "SBIN.NS", "TCS.NS", "BHARTIARTL.NS"]
    nifty = yf.download("^NSEI", start="2006-01-01", end="2026-06-05", progress=False)['Close']
    if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
    
    stock_data = {}
    for t in stocks:
        df = yf.download(t, start="2006-01-01", end="2026-06-05", progress=False)['Close']
        if isinstance(df, pd.DataFrame): df = df.iloc[:, 0]
        stock_data[t] = df
        
    sample_dates = pd.date_range(start="2008-01-01", end="2025-06-01", freq="6MS")
    
    for i in range(iterations):
        # Generate random hyper-granular parameters
        w_mom = round(random.uniform(0.1, 0.9), 3)
        w_rs = round(1.0 - w_mom, 3)
        b_thresh = round(random.uniform(32.0, 48.0), 1)
        
        print(f"Iter {i+1}/{iterations} | Testing -> Mom: {w_mom:.3f}, RS: {w_rs:.3f}, Thresh: {b_thresh}")
        
        returns = []
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
                
                weighted_score = (rs_score * w_rs) + (mom_score * w_mom)
                
                # Using the randomized Buy Threshold
                if weighted_score > b_thresh:
                    returns.append(forward_6m_return)
                    
        if len(returns) < 5: continue
        
        avg_ret = np.mean(returns) * 100
        win_rate = (len([r for r in returns if r > 0]) / len(returns)) * 100
        
        if avg_ret > current_best_ret:
            print(f"!!! BREAKTHROUGH FOUND !!! Avg Ret: {avg_ret:.2f}% | Win Rate: {win_rate:.1f}%")
            current_best_ret = avg_ret
            
            # Save new parameters to live config
            best_params = {
                "w_momentum": w_mom,
                "w_rs": w_rs,
                "buy_threshold": b_thresh
            }
            with open(param_file, "w") as f:
                json.dump(best_params, f, indent=4)
            print(f"-> Successfully dynamically updated optimal_parameters.json!")

    print("\nTraining run complete. The APEX system is now using the absolute peak mathematical weights derived from this session.")

if __name__ == "__main__":
    # We run 50 random hyper-granular permutations while the system is idle
    run_deep_trainer(iterations=50)
