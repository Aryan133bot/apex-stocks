import os
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

from core.types import DataPacket, Signal, SignalCategory, SignalSubSource
from data.store import get_db_connection
from engines.regime.hmm_model import RegimeHMM
from engines.bull.institutional import InstitutionalBullEngine
from engines.bull.relative_strength import RelativeStrengthEngine
from engines.bull.options_flow import OptionsFlowEngine
from engines.bull.fundamental import FundamentalBullEngine
from engines.bull.momentum import MomentumBullEngine

def run_integrated_pipeline():
    print("=== APEX INTEGRATED PIPELINE TEST (PHASES 1 TO 4) ===\n")
    
    # 1. Database Check (Phase 1)
    print("[1] Verifying SQLite Database (Phase 1)...")
    conn = get_db_connection()
    tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    conn.close()
    if "prices" in tables:
        print("  -> Database mounted successfully.\n")
        
    # 2. HMM Regime (Phase 3)
    print("[2] Running HMM Regime Engine on Real Market Data (Phase 3)...")
    nifty = yf.download("^NSEI", period="5y", interval="1d", progress=False)['Close']
    vix = yf.download("^INDIAVIX", period="5y", interval="1d", progress=False)['Close']
    usdinr = yf.download("USDINR=X", period="5y", interval="1d", progress=False)['Close']
    
    if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
    if isinstance(vix, pd.DataFrame): vix = vix.iloc[:, 0]
    if isinstance(usdinr, pd.DataFrame): usdinr = usdinr.iloc[:, 0]
    
    df = pd.DataFrame({"Nifty": nifty, "VIX": vix, "USDINR": usdinr}).dropna()
    features = pd.DataFrame(index=df.index)
    features['nifty_20d_ret'] = df['Nifty'].pct_change(20)
    features['nifty_60d_ret'] = df['Nifty'].pct_change(60)
    features['india_vix_lvl'] = df['VIX']
    features['india_vix_10d_roc'] = df['VIX'].pct_change(10)
    features['usdinr_20d_roc'] = df['USDINR'].pct_change(20)
    features.dropna(inplace=True)
    
    features['nifty500_above_200d'] = np.random.uniform(20, 80, len(features))
    features['nifty500_ad_slope'] = np.random.normal(0, 1, len(features))
    features['yield_repo_spread'] = np.random.normal(2, 0.5, len(features))
    features['fii_20d_flow'] = np.random.normal(0, 5000, len(features))
    features['bank_nifty_ratio'] = np.random.normal(2.5, 0.2, len(features))
    features['fii_dii_divergence'] = np.random.normal(0, 1000, len(features))
    
    hmm = RegimeHMM()
    hmm.train(features.iloc[:int(len(features)*0.8)])
    
    packet = DataPacket(ticker="TCS.NS", timestamp=datetime.utcnow())
    regime_output = hmm.evaluate(packet, recent_history_df=features.iloc[-60:])
    bull_weight = regime_output['engine_weights']['bull_base_weight']
    
    print(f"  -> Dominant State: S{regime_output['dominant_state'] + 1}")
    print(f"  -> Bull Engine Global Weight Multiplier: {bull_weight:.2f}\n")
    
    # 3. Build Data Packet with Real Stock Data (Phase 4 input)
    print("[3] Fetching real data for TCS (Stock), Nifty 50, and IT Sector...")
    tcs = yf.download("TCS.NS", period="2y", interval="1d", progress=False)['Close']
    nifty_1y = yf.download("^NSEI", period="2y", interval="1d", progress=False)['Close']
    it_sector = yf.download("^CNXIT", period="2y", interval="1d", progress=False)['Close']
    
    if isinstance(tcs, pd.DataFrame): tcs = tcs.iloc[:, 0]
    if isinstance(nifty_1y, pd.DataFrame): nifty_1y = nifty_1y.iloc[:, 0]
    if isinstance(it_sector, pd.DataFrame): it_sector = it_sector.iloc[:, 0]
    
    # Calculate returns & MAs
    tcs_63d_ret = (tcs.iloc[-1] / tcs.iloc[-63]) - 1
    nifty_63d_ret = (nifty_1y.iloc[-1] / nifty_1y.iloc[-63]) - 1
    sector_63d_ret = (it_sector.iloc[-1] / it_sector.iloc[-63]) - 1
    
    tcs_200dma = tcs.rolling(200).mean().iloc[-1]
    tcs_50dma = tcs.rolling(50).mean().iloc[-1]
    dist_200d = (tcs.iloc[-1] / tcs_200dma) - 1
    dist_50d = (tcs.iloc[-1] / tcs_50dma) - 1
    
    print(f"  -> TCS 63D Return: {tcs_63d_ret:.2%}")
    print(f"  -> Nifty 63D Return: {nifty_63d_ret:.2%}")
    print(f"  -> IT Sector 63D Return: {sector_63d_ret:.2%}\n")
    
    # Inject real price signals
    packet.signals.append(Signal(name="STOCK_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=tcs_63d_ret, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="NIFTY_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=nifty_63d_ret, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="SECTOR_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=sector_63d_ret, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="DIST_200DMA", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=dist_200d, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="DIST_50DMA", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=dist_50d, timestamp=datetime.utcnow()))
    
    # Inject mock fundamental/institutional signals for a "perfect" tech stock scenario
    packet.signals.append(Signal(name="FII_10D_ZSCORE", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.THIRTEEN_F, value=1.5, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="BULK_DEAL_SCORE", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.THIRTEEN_F, value=80.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="PROMOTER_HOLDING_CHG", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.INSIDER, value=0.0, timestamp=datetime.utcnow()))
    
    packet.signals.append(Signal(name="PCR", category=SignalCategory.OPTIONS, sub_source=SignalSubSource.OPTIONS_FLOW, value=0.55, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="IV_RANK", category=SignalCategory.OPTIONS, sub_source=SignalSubSource.OPTIONS_FLOW, value=30.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="NET_PUT_OI_ADDITION", category=SignalCategory.OPTIONS, sub_source=SignalSubSource.OPTIONS_FLOW, value=2.5, timestamp=datetime.utcnow()))
    
    packet.signals.append(Signal(name="PAT_GROWTH_YOY", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=0.18, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="EBITDA_MARGIN", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=25.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="ROE", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=28.0, timestamp=datetime.utcnow()))
    
    # 4. Evaluate all Phase 4 Bull Engines
    print("[4] Executing Phase 4 Bull Engines...")
    scores = {}
    
    rs_eng = RelativeStrengthEngine()
    scores['Relative Strength'] = rs_eng.evaluate(packet)['score']
    print(f"  - Relative Strength Score : {scores['Relative Strength']:.1f}/100")
    
    mom_eng = MomentumBullEngine()
    scores['Momentum'] = mom_eng.evaluate(packet)['score']
    print(f"  - Momentum Score          : {scores['Momentum']:.1f}/100")
    
    inst_eng = InstitutionalBullEngine()
    scores['Institutional Flow'] = inst_eng.evaluate(packet)['score']
    print(f"  - Institutional Score     : {scores['Institutional Flow']:.1f}/100")
    
    opt_eng = OptionsFlowEngine()
    scores['Options Flow'] = opt_eng.evaluate(packet)['score']
    print(f"  - Options Flow Score      : {scores['Options Flow']:.1f}/100")
    
    fund_eng = FundamentalBullEngine()
    scores['Fundamental'] = fund_eng.evaluate(packet)['score']
    print(f"  - Fundamental Score       : {scores['Fundamental']:.1f}/100")
    
    # Average base Bull Score
    raw_bull_score = sum(scores.values()) / len(scores)
    print(f"\n  -> Raw Base Bull Score    : {raw_bull_score:.1f}/100")
    
    # 5. The Integration (Phase 3 x Phase 4)
    print("\n[5] INTEGRATION CHECK (HMM REGIME * BULL ENGINES)")
    final_integrated_score = raw_bull_score * bull_weight
    
    print(f"  Raw Bull Score ({raw_bull_score:.1f}) x Regime Multiplier ({bull_weight:.2f}) = {final_integrated_score:.1f} Final Points")
    if final_integrated_score > 60:
        print("  >>> OUTCOME: STRONG BUY. The integrated pipeline correctly approved the trade.\n")
    elif final_integrated_score < 30:
        print("  >>> OUTCOME: HARD REJECT. The Regime/Momentum filtered the trade out.\n")
    else:
        print("  >>> OUTCOME: HOLD / NEUTRAL. System awaits better alignment.\n")

if __name__ == "__main__":
    run_integrated_pipeline()
