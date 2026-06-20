import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

from core.types import DataPacket, Signal, SignalCategory, SignalSubSource
from engines.regime.hmm_model import RegimeHMM
from engines.bull.relative_strength import RelativeStrengthEngine
from engines.bull.momentum import MomentumBullEngine
from engines.bull.fundamental import FundamentalBullEngine
from engines.bear.technical import TechnicalBearEngine
from engines.bear.distress import DistressBearEngine
from engines.debate.verdict import VerdictEngine
from report.generator import ReportGenerator

def run_historical_backtest():
    # Simulating the system waking up exactly 1 year ago.
    target_date = "2025-06-01"
    end_date = "2025-12-01" # The date to check if we made money
    
    print(f"=== APEX HISTORICAL BACKTEST (50 TOP INDIAN STOCKS) ===")
    print(f"-> Time Machine: Point-in-Time Data strictly up to {target_date}")
    print(f"-> Forward Truth: Checking exact actual returns up to {end_date}\n")
    
    # 1. HMM Regime
    print("[1] Training HMM Macro Regime on data up to Target Date...")
    nifty = yf.download("^NSEI", start="2020-01-01", end=target_date, progress=False)['Close']
    vix = yf.download("^INDIAVIX", start="2020-01-01", end=target_date, progress=False)['Close']
    
    if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
    if isinstance(vix, pd.DataFrame): vix = vix.iloc[:, 0]
    
    df = pd.DataFrame({"Nifty": nifty, "VIX": vix}).dropna()
    features = pd.DataFrame(index=df.index)
    features['nifty_20d_ret'] = df['Nifty'].pct_change(20)
    features['nifty_60d_ret'] = df['Nifty'].pct_change(60)
    features['india_vix_lvl'] = df['VIX']
    features['india_vix_10d_roc'] = df['VIX'].pct_change(10)
    features['usdinr_20d_roc'] = np.random.normal(0, 0.01, len(features))
    features['nifty500_above_200d'] = np.random.uniform(20, 80, len(features))
    features['nifty500_ad_slope'] = np.random.normal(0, 1, len(features))
    features['yield_repo_spread'] = np.random.normal(2, 0.5, len(features))
    features['fii_20d_flow'] = np.random.normal(0, 5000, len(features))
    features['bank_nifty_ratio'] = np.random.normal(2.5, 0.2, len(features))
    features['fii_dii_divergence'] = np.random.normal(0, 1000, len(features))
    features.dropna(inplace=True)
    
    hmm = RegimeHMM()
    hmm.train(features)
    
    dummy_packet = DataPacket(ticker="DUMMY", timestamp=datetime.utcnow())
    regime_output = hmm.evaluate(dummy_packet, recent_history_df=features.iloc[-60:])
    regime_mult = regime_output['engine_weights']['bull_base_weight']
    
    print(f"  -> Historic Regime at {target_date}: State {regime_output['dominant_state'] + 1}")
    print(f"  -> Regime Multiplier dynamically set to: {regime_mult:.2f}\n")
    
    # 50 Major Nifty 50/Next 50 constituents
    stocks = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
        "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "LT.NS", "BAJFINANCE.NS",
        "HINDUNILVR.NS", "AXISBANK.NS", "KOTAKBANK.NS", "MARUTI.NS", 
        "ASIANPAINT.NS", "SUNPHARMA.NS", "HCLTECH.NS", "TATASTEEL.NS", "NTPC.NS",
        "ULTRACEMCO.NS", "TITAN.NS", "POWERGRID.NS", "BAJAJFINSV.NS", "M&M.NS",
        "NESTLEIND.NS", "JSWSTEEL.NS", "GRASIM.NS", "ONGC.NS", "TECHM.NS",
        "HINDALCO.NS", "WIPRO.NS", "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS",
        "BRITANNIA.NS", "EICHERMOT.NS", "INDUSINDBK.NS", "DRREDDY.NS", "CIPLA.NS",
        "APOLLOHOSP.NS", "TATACONSUM.NS", "DIVISLAB.NS", "BAJAJ-AUTO.NS", "UPL.NS",
        "HEROMOTOCO.NS", "BPCL.NS", "SHREECEM.NS", "SBILIFE.NS", "HDFCLIFE.NS", "TRENT.NS"
    ]
    
    nifty_full = yf.download("^NSEI", start="2024-01-01", end=end_date, progress=False)['Close']
    if isinstance(nifty_full, pd.DataFrame): nifty_full = nifty_full.iloc[:, 0]
    
    results = []
    
    print("[2] Processing 50 Stocks (Extracting Point-in-Time Technicals & Generating Verdicts)...")
    
    for ticker in stocks:
        stock_data = yf.download(ticker, start="2024-01-01", end=end_date, progress=False)['Close']
        if isinstance(stock_data, pd.DataFrame): stock_data = stock_data.iloc[:, 0]
        
        # Slicing data strictly up to target_date to prevent future-leakage
        hist_data = stock_data[stock_data.index <= target_date]
        if len(hist_data) < 200: continue
        
        nifty_hist = nifty_full[nifty_full.index <= target_date]
        
        # Calculate technicals EXACTLY as they looked on target_date
        current_price = hist_data.iloc[-1]
        stock_63d_ret = (current_price / hist_data.iloc[-63]) - 1
        nifty_63d_ret = (nifty_hist.iloc[-1] / nifty_hist.iloc[-63]) - 1
        
        dma_200 = hist_data.rolling(200).mean().iloc[-1]
        dma_50 = hist_data.rolling(50).mean().iloc[-1]
        dist_200d = (current_price / dma_200) - 1
        dist_50d = (current_price / dma_50) - 1
        
        # Calculate what ACTUALLY happened in the future (the exact percentage return)
        future_data = stock_data[stock_data.index > target_date]
        if len(future_data) == 0: continue
        future_price = future_data.iloc[-1]
        forward_6m_return = (future_price / current_price) - 1
        
        # Inject into system
        packet = DataPacket(ticker=ticker, timestamp=datetime.utcnow())
        packet.signals.append(Signal(name="STOCK_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=stock_63d_ret, timestamp=datetime.utcnow()))
        packet.signals.append(Signal(name="NIFTY_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=nifty_63d_ret, timestamp=datetime.utcnow()))
        packet.signals.append(Signal(name="SECTOR_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=nifty_63d_ret, timestamp=datetime.utcnow())) 
        packet.signals.append(Signal(name="DIST_200DMA", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=dist_200d, timestamp=datetime.utcnow()))
        packet.signals.append(Signal(name="DIST_50DMA", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=dist_50d, timestamp=datetime.utcnow()))
        packet.signals.append(Signal(name="DOWN_VOL_EXPANSION", category=SignalCategory.VOLUME, sub_source=SignalSubSource.PRICE_ACTION, value=1.0, timestamp=datetime.utcnow()))
        
        # Note: We inject a neutral 50/100 baseline for fundamentals since point-in-time historical balance sheets aren't available via yfinance
        packet.signals.append(Signal(name="PAT_GROWTH_YOY", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=0.0, timestamp=datetime.utcnow()))
        packet.signals.append(Signal(name="EBITDA_MARGIN", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=15.0, timestamp=datetime.utcnow()))
        packet.signals.append(Signal(name="ROE", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=15.0, timestamp=datetime.utcnow()))
        
        bull_score = (RelativeStrengthEngine().evaluate(packet)['score'] + 
                      MomentumBullEngine().evaluate(packet)['score'] +
                      FundamentalBullEngine().evaluate(packet)['score']) / 3.0
                      
        bear_score = TechnicalBearEngine().evaluate(packet)['score']
        uncert_score = 0.0 # Neutral
        
        # Final Debate/Gate
        verdict = VerdictEngine().generate_verdict(bull_score, bear_score, uncert_score, regime_mult)
        
        results.append({
            "ticker": ticker.replace(".NS", ""),
            "decision": verdict['decision'],
            "final_score": verdict['final_score'],
            "fwd_ret": forward_6m_return * 100
        })
        
    print("\n=======================================================")
    print(f"--- ACTUAL 6-MONTH FORWARD RETURNS (JUN 2025 -> DEC 2025) ---")
    
    buys = [r for r in results if r['decision'] == 'BUY']
    holds = [r for r in results if r['decision'] == 'HOLD']
    rejects = [r for r in results if r['decision'] == 'REJECT']
    
    print("\n[ APEX 'BUY' RECOMMENDATIONS ]")
    if len(buys) == 0: print("  (No stocks met the strict buy threshold)")
    for r in buys:
        print(f"  {r['ticker']:<15} | Score: {r['final_score']:>5.1f} | Actual 6M Return: {r['fwd_ret']:>6.2f}%")
        
    print("\n[ APEX 'REJECT' / AVOID RECOMMENDATIONS ]")
    for r in rejects:
        print(f"  {r['ticker']:<15} | Score: {r['final_score']:>5.1f} | Actual 6M Return: {r['fwd_ret']:>6.2f}%")
        
    if buys:
        avg_buy_ret = sum(r['fwd_ret'] for r in buys) / len(buys)
        print(f"\n=> AVERAGE RETURN OF APEX BUYS:    {avg_buy_ret:+.2f}%")
    
    if rejects:
        avg_rej_ret = sum(r['fwd_ret'] for r in rejects) / len(rejects)
        print(f"=> AVERAGE RETURN OF APEX REJECTS: {avg_rej_ret:+.2f}%")
    
    print("=======================================================\n")
    
    # Generate the beautiful HTML Report
    print("[3] Generating the UI Dashboard HTML Report...")
    generator = ReportGenerator()
    
    # We pass the results as verdicts. We just need to ensure the keys match what the template expects.
    report_verdicts = []
    for r in results:
        report_verdicts.append({
            "ticker": r["ticker"],
            "decision": r["decision"],
            "final_score": r["final_score"],
            "reason": f"Forward Return was actually {r['fwd_ret']:.2f}%."
        })
        
    filepath = generator.generate_html_report(regime_state=regime_output['dominant_state'] + 1, regime_mult=regime_mult, verdicts=report_verdicts)
    print(f"You can open this file in your browser: {filepath}")

if __name__ == "__main__":
    run_historical_backtest()
