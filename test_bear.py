import pandas as pd
import yfinance as yf
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

from core.types import DataPacket, Signal, SignalCategory, SignalSubSource
from engines.bear.promoter import PromoterBearEngine
from engines.bear.distress import DistressBearEngine
from engines.bear.distribution import DistributionBearEngine
from engines.bear.event_macro import MacroBearEngine
from engines.bear.technical import TechnicalBearEngine

def test_bear_engines():
    print("=== TESTING PHASE 5: BEAR ENGINES WITH REAL AND SIMULATED DISTRESS DATA ===\n")
    
    # 1. Pull real data for a stock that experienced extreme breakdown (PAYTM)
    print("[1] Fetching real data for PAYTM.NS to test Technical Breakdown Engine...")
    paytm_close = yf.download("PAYTM.NS", period="1y", interval="1d", progress=False)['Close']
    paytm_vol = yf.download("PAYTM.NS", period="1y", interval="1d", progress=False)['Volume']
    
    if isinstance(paytm_close, pd.DataFrame): paytm_close = paytm_close.iloc[:, 0]
    if isinstance(paytm_vol, pd.DataFrame): paytm_vol = paytm_vol.iloc[:, 0]
    
    # Calculate exactly how far it is from the 200DMA today
    paytm_200dma = paytm_close.rolling(200).mean().iloc[-1]
    dist_200d = (paytm_close.iloc[-1] / paytm_200dma) - 1
    
    # Calculate volume expansion (Is today's selling volume heavier than the 30D average?)
    avg_vol = paytm_vol.rolling(30).mean().iloc[-1]
    curr_vol = paytm_vol.iloc[-1]
    vol_expansion = (curr_vol / avg_vol) if avg_vol > 0 else 1.0
    
    print(f"  -> PAYTM Distance from 200DMA: {dist_200d:.2%}")
    print(f"  -> PAYTM Down-Volume Expansion Multiple: {vol_expansion:.2f}x\n")
    
    # 2. Build the DataPacket
    packet = DataPacket(ticker="PAYTM.NS", timestamp=datetime.utcnow())
    
    # Inject real Technical Signals
    packet.signals.append(Signal(name="DIST_200DMA", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=dist_200d, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="DOWN_VOL_EXPANSION", category=SignalCategory.VOLUME, sub_source=SignalSubSource.PRICE_ACTION, value=vol_expansion, timestamp=datetime.utcnow()))
    
    # Inject massive simulated distress (e.g. Promoter is highly leveraged, Auditor flagged accounts, FII is dumping)
    print("[2] Injecting severe structural distress signals (NCLT, 40% Pledges, FII dumping)...")
    packet.signals.append(Signal(name="PROMOTER_PLEDGE_PCT", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.INSIDER, value=40.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="PROMOTER_PLEDGE_CHG", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.INSIDER, value=5.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="PROMOTER_HOLDING_CHG", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.INSIDER, value=-2.5, timestamp=datetime.utcnow()))
    
    packet.signals.append(Signal(name="IBC_NCLT_STATUS", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=1.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="AUDITOR_QUALIFICATION", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=1.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="GROSS_NPA_PCT", category=SignalCategory.FUNDAMENTAL, sub_source=SignalSubSource.FINANCIAL_STATEMENT, value=8.0, timestamp=datetime.utcnow()))
    
    packet.signals.append(Signal(name="FII_10D_ZSCORE", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.THIRTEEN_F, value=-2.5, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="BULK_DEAL_SELLERS", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.THIRTEEN_F, value=85.0, timestamp=datetime.utcnow()))
    
    packet.signals.append(Signal(name="MACRO_EVENT_RISK", category=SignalCategory.MACRO, sub_source=SignalSubSource.NEWS_ARTICLE, value=80.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="USDINR_DEPRECIATION", category=SignalCategory.MACRO, sub_source=SignalSubSource.PRICE_ACTION, value=30.0, timestamp=datetime.utcnow()))
    
    # 3. Evaluate Bear Engines
    print("\n[3] Executing Phase 5 Bear Engines (High score = High Risk/Veto)...\n")
    
    promoter_eng = PromoterBearEngine()
    print(f"  - Promoter Risk Score     : {promoter_eng.evaluate(packet)['score']:.1f}/100")
    
    distress_eng = DistressBearEngine()
    print(f"  - Financial Distress Score: {distress_eng.evaluate(packet)['score']:.1f}/100")
    
    distrib_eng = DistributionBearEngine()
    print(f"  - FII Distribution Score  : {distrib_eng.evaluate(packet)['score']:.1f}/100")
    
    macro_eng = MacroBearEngine()
    print(f"  - Macro Headwind Score    : {macro_eng.evaluate(packet)['score']:.1f}/100")
    
    tech_eng = TechnicalBearEngine()
    print(f"  - Technical Tail Risk     : {tech_eng.evaluate(packet)['score']:.1f}/100")
    
if __name__ == "__main__":
    test_bear_engines()
