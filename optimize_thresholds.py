import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

from core.types import DataPacket, Signal, SignalCategory, SignalSubSource
from engines.regime.hmm_model import RegimeHMM
from engines.bull.relative_strength import RelativeStrengthEngine
from engines.bull.momentum import MomentumBullEngine
from engines.bull.fundamental import FundamentalBullEngine
from engines.bear.technical import TechnicalBearEngine

def run_optimizer():
    sample_dates = ["2021-06-01", "2022-06-01", "2023-06-01", "2024-06-01", "2025-06-01"]
    stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "ITC.NS", "LT.NS"]
    
    print("=== APEX LONG-TERM THRESHOLD OPTIMIZER ===")
    print(f"Sampling Dates: {sample_dates}")
    print("Extracting raw score distributions to calibrate the Verdict Engine...\n")
    
    # 1. Pre-download data to save time
    print("Downloading historical data...")
    nifty = yf.download("^NSEI", start="2018-01-01", end="2026-06-01", progress=False)['Close']
    vix = yf.download("^INDIAVIX", start="2018-01-01", end="2026-06-01", progress=False)['Close']
    if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
    if isinstance(vix, pd.DataFrame): vix = vix.iloc[:, 0]
    
    stock_data_map = {}
    for t in stocks:
        df = yf.download(t, start="2018-01-01", end="2026-06-01", progress=False)['Close']
        if isinstance(df, pd.DataFrame): df = df.iloc[:, 0]
        stock_data_map[t] = df
        
    all_results = []

    for target_date in sample_dates:
        print(f"\n[Processing Date: {target_date}]")
        
        # Train HMM up to target date
        df_hmm = pd.DataFrame({"Nifty": nifty[nifty.index <= target_date], "VIX": vix[vix.index <= target_date]}).dropna()
        if len(df_hmm) < 250: continue
        
        features = pd.DataFrame(index=df_hmm.index)
        features['nifty_20d_ret'] = df_hmm['Nifty'].pct_change(20)
        features['nifty_60d_ret'] = df_hmm['Nifty'].pct_change(60)
        features['india_vix_lvl'] = df_hmm['VIX']
        features['india_vix_10d_roc'] = df_hmm['VIX'].pct_change(10)
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
        print(f"  Regime Multiplier: {regime_mult:.2f}")
        
        for ticker in stocks:
            stock_series = stock_data_map[ticker]
            hist_data = stock_series[stock_series.index <= target_date]
            if len(hist_data) < 200: continue
            
            nifty_hist = nifty[nifty.index <= target_date]
            
            current_price = hist_data.iloc[-1]
            stock_63d_ret = (current_price / hist_data.iloc[-63]) - 1
            nifty_63d_ret = (nifty_hist.iloc[-1] / nifty_hist.iloc[-63]) - 1
            
            dma_200 = hist_data.rolling(200).mean().iloc[-1]
            dma_50 = hist_data.rolling(50).mean().iloc[-1]
            dist_200d = (current_price / dma_200) - 1
            dist_50d = (current_price / dma_50) - 1
            
            future_data = stock_series[stock_series.index > target_date]
            if len(future_data) < 120: continue # Need at least 6 months forward data
            future_price = future_data.iloc[120] # Roughly 6 months forward
            forward_6m_return = (future_price / current_price) - 1
            
            packet = DataPacket(ticker=ticker, timestamp=datetime.utcnow())
            packet.signals.append(Signal("STOCK_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, stock_63d_ret, datetime.utcnow()))
            packet.signals.append(Signal("NIFTY_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, nifty_63d_ret, datetime.utcnow()))
            packet.signals.append(Signal("SECTOR_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, nifty_63d_ret, datetime.utcnow()))
            packet.signals.append(Signal("DIST_200DMA", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, dist_200d, datetime.utcnow()))
            packet.signals.append(Signal("DIST_50DMA", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, dist_50d, datetime.utcnow()))
            packet.signals.append(Signal("DOWN_VOL_EXPANSION", SignalCategory.VOLUME, SignalSubSource.PRICE_ACTION, 1.0, datetime.utcnow()))
            
            # Since we lack historical fundamentals, we inject a highly bullish synthetic fundamental profile 
            # to represent what APEX would see if the stock was fundamentally sound at that time.
            packet.signals.append(Signal("PAT_GROWTH_YOY", SignalCategory.FUNDAMENTAL, SignalSubSource.FINANCIAL_STATEMENT, 0.25, datetime.utcnow()))
            packet.signals.append(Signal("EBITDA_MARGIN", SignalCategory.FUNDAMENTAL, SignalSubSource.FINANCIAL_STATEMENT, 25.0, datetime.utcnow()))
            packet.signals.append(Signal("ROE", SignalCategory.FUNDAMENTAL, SignalSubSource.FINANCIAL_STATEMENT, 20.0, datetime.utcnow()))
            
            bull_score = (RelativeStrengthEngine().evaluate(packet)['score'] + 
                          MomentumBullEngine().evaluate(packet)['score'] +
                          FundamentalBullEngine().evaluate(packet)['score']) / 3.0
            
            adjusted_bull_score = bull_score * regime_mult
            
            all_results.append({
                "ticker": ticker,
                "date": target_date,
                "raw_bull": bull_score,
                "adj_bull": adjusted_bull_score,
                "regime_mult": regime_mult,
                "fwd_ret": forward_6m_return * 100
            })
            
    print("\n=== SCORE DISTRIBUTION ANALYSIS ===")
    df_res = pd.DataFrame(all_results)
    print(df_res.describe()[['raw_bull', 'adj_bull', 'fwd_ret']])
    
    print("\n=== TESTING DIFFERENT BUY THRESHOLDS ===")
    thresholds = [30, 35, 40, 45, 50, 55, 60]
    for th in thresholds:
        buys = df_res[df_res['adj_bull'] >= th]
        win_rate = (len(buys[buys['fwd_ret'] > 0]) / len(buys) * 100) if len(buys) > 0 else 0
        avg_ret = buys['fwd_ret'].mean() if len(buys) > 0 else 0
        print(f"Threshold: {th:2} | Total Trades: {len(buys):3} | Win Rate: {win_rate:5.1f}% | Avg 6M Return: {avg_ret:5.1f}%")

if __name__ == "__main__":
    run_optimizer()
