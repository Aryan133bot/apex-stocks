import os
import pandas as pd
import yfinance as yf
from datetime import datetime

from core.types import DataPacket, Signal, SignalCategory, SignalSubSource
from engines.bull.relative_strength import RelativeStrengthEngine
from engines.bull.institutional import InstitutionalBullEngine

def test_bull_engines_real_data():
    print("--- TESTING PHASE 4: BULL ENGINES WITH REAL WORLD DATA ---")
    
    # 1. Pull real data using yfinance
    print("\nFetching real 3-month data for RELIANCE (Stock), ^NSEI (Nifty 50), and ^CNXENERGY (Sector)...")
    
    # Reliance Industries on NSE
    stock = yf.download("RELIANCE.NS", period="6mo", interval="1d", progress=False)['Close']
    # Nifty 50
    nifty = yf.download("^NSEI", period="6mo", interval="1d", progress=False)['Close']
    # Nifty Energy Sector Index
    sector = yf.download("^CNXENERGY", period="6mo", interval="1d", progress=False)['Close']
    
    # Flatten multi-index columns
    if isinstance(stock, pd.DataFrame): stock = stock.iloc[:, 0]
    if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
    if isinstance(sector, pd.DataFrame): sector = sector.iloc[:, 0]
    
    # Calculate exact 63-Day (approx 3 trading months) returns
    stock_63d_ret = (stock.iloc[-1] - stock.iloc[-63]) / stock.iloc[-63]
    nifty_63d_ret = (nifty.iloc[-1] - nifty.iloc[-63]) / nifty.iloc[-63]
    sector_63d_ret = (sector.iloc[-1] - sector.iloc[-63]) / sector.iloc[-63]
    
    print("\n[REAL DATA EXTRACTED]")
    print(f"RELIANCE 63-Day Return : {stock_63d_ret:.2%}")
    print(f"NIFTY 50 63-Day Return : {nifty_63d_ret:.2%}")
    print(f"ENERGY SEC 63-Day Return: {sector_63d_ret:.2%}")
    
    # 2. Build the DataPacket
    packet = DataPacket(ticker="RELIANCE.NS", timestamp=datetime.utcnow())
    
    # Add Relative Strength signals
    packet.signals.append(Signal(name="STOCK_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=stock_63d_ret, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="NIFTY_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=nifty_63d_ret, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="SECTOR_63D_RET", category=SignalCategory.PRICE, sub_source=SignalSubSource.PRICE_ACTION, value=sector_63d_ret, timestamp=datetime.utcnow()))
    
    # Add Institutional signals (mocking these since real-time FII stock-level data requires NSE CSV parsing)
    # Let's mock a scenario where FII is heavily buying (+2.5 z-score), but promoters are flat (0.0).
    packet.signals.append(Signal(name="FII_10D_ZSCORE", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.THIRTEEN_F, value=2.5, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="BULK_DEAL_SCORE", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.THIRTEEN_F, value=60.0, timestamp=datetime.utcnow()))
    packet.signals.append(Signal(name="PROMOTER_HOLDING_CHG", category=SignalCategory.INSTITUTIONAL, sub_source=SignalSubSource.INSIDER, value=0.0, timestamp=datetime.utcnow()))

    # 3. Evaluate Relative Strength
    print("\n--- EVALUATING RELATIVE STRENGTH ENGINE ---")
    rs_engine = RelativeStrengthEngine()
    rs_results = rs_engine.evaluate(packet)
    
    print(f"Stock vs Nifty Score    : {rs_results['rs1_nifty_score']:.1f}/100")
    print(f"Stock vs Sector Score   : {rs_results['rs2_sector_score']:.1f}/100")
    print(f"Sector vs Nifty Score   : {rs_results['rs3_sector_nifty_score']:.1f}/100")
    print(f">> FINAL RS SCORE       : {rs_results['score']:.1f}/100")
    
    # 4. Evaluate Institutional Flow
    print("\n--- EVALUATING INSTITUTIONAL FLOW ENGINE ---")
    inst_engine = InstitutionalBullEngine()
    inst_results = inst_engine.evaluate(packet)
    
    print(f"FII Flow Score          : {inst_results['fii_flow_score']:.1f}/100  (Heavy Accumulation)")
    print(f"Bulk Deal Score         : {inst_results['bulk_deal_score']:.1f}/100")
    print(f"Promoter Buying Score   : {inst_results['promoter_score']:.1f}/100  (Flat/No Change)")
    print(f">> FINAL INST SCORE     : {inst_results['score']:.1f}/100")

if __name__ == "__main__":
    test_bull_engines_real_data()
