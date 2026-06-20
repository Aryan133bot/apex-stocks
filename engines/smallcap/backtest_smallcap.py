import os
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

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

def setup_data():
    print("1. Fetching 2-Year Historical OHLCV for Universe...")
    stock_data = {}
    for ticker in SMALL_CAP_UNIVERSE:
        df = yf.download(f"{ticker}.NS", period="2y", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            stock_data[ticker] = df
            
    print("2. Fetching Static Fundamentals...")
    fund_fetcher = FundamentalFetcher()
    share_fetcher = ShareholdingFetcher()
    
    static_data = {}
    for ticker in SMALL_CAP_UNIVERSE:
        raw_fund = fund_fetcher.get_fundamentals(ticker, use_cache=True)
        metrics = fund_fetcher.parse_quality_metrics(raw_fund)
        promoter = share_fetcher.get_promoter_holding(ticker)
        pledge = share_fetcher.get_pledged_data(ticker)
        static_data[ticker] = {
            "metrics": metrics,
            "promoter": promoter,
            "pledge": pledge
        }
    return stock_data, static_data

def run_simulation(stock_data, static_data, stop_loss_pct, max_holding_days):
    gate = SmallCapGate()
    classifier = PatternClassifier()
    
    if "SUZLON" not in stock_data:
        base_df = list(stock_data.values())[0]
    else:
        base_df = stock_data["SUZLON"]
        
    all_dates = base_df.index
    if len(all_dates) < 130:
        return None
        
    backtest_dates = all_dates[-105:] # Approx 5 months
    
    trades = []
    
    # We must stop early enough to allow the last trade to hit its max_holding_days
    for T_idx in range(len(backtest_dates) - max_holding_days): 
        current_date = backtest_dates[T_idx]
        
        for ticker, df in stock_data.items():
            sliced_df = df[df.index <= current_date]
            if len(sliced_df) < 250:
                continue 
                
            stats = static_data[ticker]
            
            try:
                current_price = float(sliced_df['Close'].iloc[-1])
            except TypeError:
                continue
                
            if not (10 <= current_price <= 1500):
                continue
                
            hist_20d = sliced_df.tail(20)
            avg_vol_20d = float(hist_20d['Volume'].mean())
            today_vol = float(sliced_df['Volume'].iloc[-1])
            
            avg_turnover_20d = avg_vol_20d * current_price
            today_turnover = today_vol * current_price
            
            gate_pass, _ = gate.run_gate_zero(stats["metrics"], stats["promoter"], avg_turnover_20d, today_turnover)
            if not gate_pass: continue
            
            manip_clean, _ = gate.run_manipulation_screen(sliced_df, stats["metrics"], stats["pledge"])
            if not manip_clean: continue
            
            pattern_type, score = classifier.classify(sliced_df, stats["metrics"], stats["promoter"])
            if pattern_type is None: continue
            
            # Executing Trade
            future_df = df[df.index > current_date]
            if future_df.empty: continue
            
            entry_date = future_df.index[0]
            entry_price = float(future_df['Open'].iloc[0])
            stop_loss = entry_price * (1.0 - stop_loss_pct)
            
            trade = {
                "ticker": ticker,
                "status": "OPEN",
                "pnl_pct": 0.0
            }
            
            holding_period = future_df.head(max_holding_days)
            for h_idx, (date, row) in enumerate(holding_period.iterrows()):
                low_price = float(row['Low'])
                if low_price <= stop_loss:
                    trade["status"] = "STOPPED OUT"
                    trade["pnl_pct"] = - (stop_loss_pct * 100.0)
                    break
                    
                if h_idx == len(holding_period) - 1:
                    trade["status"] = "CLOSED (TIME EXPIRED)"
                    exit_price = float(row['Close'])
                    trade["pnl_pct"] = ((exit_price - entry_price) / entry_price) * 100.0
                    break
                    
            if trade["status"] != "OPEN":
                trades.append(trade)

    if not trades:
        return {"signals": 0, "win_rate": 0, "avg_pnl": 0, "total_pnl": 0}
        
    wins = [t for t in trades if t["pnl_pct"] > 0]
    win_rate = (len(wins) / len(trades)) * 100
    avg_pnl = sum(t["pnl_pct"] for t in trades) / len(trades)
    total_pnl = sum(t["pnl_pct"] for t in trades)
    
    return {
        "signals": len(trades),
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "total_pnl": total_pnl
    }

def run_grid_search():
    print("=== APEX SMALL-CAP HYPERPARAMETER OPTIMIZER ===")
    stock_data, static_data = setup_data()
    
    # Grid of Parameters to test
    stop_losses = [0.05, 0.10, 0.15] # 5%, 10%, 15%
    holding_periods = [10, 20, 30, 40] # Days
    
    results = []
    
    print("\n3. Executing Grid Search Over 12 Configurations...")
    print("-" * 75)
    print(f"{'Stop Loss':<15} | {'Hold Days':<12} | {'Signals':<10} | {'Win Rate':<10} | {'Total PnL':<10}")
    print("-" * 75)
    
    for sl in stop_losses:
        for hd in holding_periods:
            res = run_simulation(stock_data, static_data, sl, hd)
            if res:
                results.append({
                    "stop_loss": sl,
                    "hold_days": hd,
                    "signals": res["signals"],
                    "win_rate": res["win_rate"],
                    "avg_pnl": res["avg_pnl"],
                    "total_pnl": res["total_pnl"]
                })
                print(f"-{sl*100:<14.0f} | {hd:<12} | {res['signals']:<10} | {res['win_rate']:<9.1f}% | +{res['total_pnl']:<10.2f}%")
                
    # Sort by Total PnL descending
    results.sort(key=lambda x: x["total_pnl"], reverse=True)
    
    print("\n" + "="*50)
    print("OPTIMIZATION COMPLETE: TOP 3 CONFIGURATIONS")
    print("="*50)
    for i, r in enumerate(results[:3], 1):
        print(f"Rank {i}: Stop Loss: -{r['stop_loss']*100:.0f}%, Hold: {r['hold_days']} Days -> Total PnL: +{r['total_pnl']:.2f}%")

if __name__ == "__main__":
    run_grid_search()
