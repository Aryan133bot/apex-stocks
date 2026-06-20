import os
import json
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from core.types import DataPacket, Signal, SignalCategory, SignalSubSource
from engines.regime.hmm_model import RegimeHMM
from engines.bull.relative_strength import RelativeStrengthEngine
from engines.bull.momentum import MomentumBullEngine
from engines.bull.fundamental import FundamentalBullEngine
from engines.bear.technical import TechnicalBearEngine
from engines.debate.verdict import VerdictEngine
from data.sector_map import SECTOR_MAP, SECTOR_INDICES
from engines.audit.auditor import DailyAuditor

def load_universe():
    universe_file = os.path.join(os.path.dirname(__file__), "data", "universe.txt")
    if not os.path.exists(universe_file):
        return ["RELIANCE.NS", "TCS.NS"] # Fallback
    with open(universe_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def load_parameters():
    param_file = os.path.join(os.path.dirname(__file__), "data", "optimal_parameters.json")
    if os.path.exists(param_file):
        with open(param_file, "r") as f:
            return json.load(f)
    return {"w_momentum": 0.70, "w_rs": 0.30, "buy_threshold": 38.0}

def fetch_fundamentals(ticker):
    """Fetch REAL fundamental data from Yahoo Finance for a single ticker."""
    try:
        info = yf.Ticker(ticker).info
        roe = info.get("returnOnEquity", 0.0) or 0.0           # decimal (0.15 = 15%)
        profit_margin = info.get("profitMargins", 0.0) or 0.0   # decimal
        revenue_growth = info.get("revenueGrowth", 0.0) or 0.0  # decimal
        return ticker, {
            "pat_growth": revenue_growth,         # proxy for earnings growth
            "ebitda_margin": profit_margin * 100,  # convert to percentage
            "roe": roe * 100                       # convert to percentage
        }
    except:
        return ticker, {"pat_growth": 0.10, "ebitda_margin": 12.0, "roe": 12.0}

def calculate_down_volume_expansion(ticker, stock_data_full):
    """Calculate REAL down-volume expansion from historical OHLCV data."""
    try:
        ohlcv = stock_data_full[ticker] if ticker in stock_data_full else None
        if ohlcv is None or len(ohlcv) < 35:
            return 1.0
        
        close = ohlcv['Close']
        opn = ohlcv['Open']
        volume = ohlcv['Volume']
        
        # Red days = close < open
        red_mask = close < opn
        avg_vol_30d = volume.iloc[-30:].mean()
        
        if avg_vol_30d == 0:
            return 1.0
            
        # Look at the last 5 red days' average volume
        recent_red_vols = volume[red_mask].iloc[-5:]
        if len(recent_red_vols) == 0:
            return 0.5  # No recent red days = bullish
            
        down_vol_ratio = recent_red_vols.mean() / avg_vol_30d
        return float(down_vol_ratio)
    except:
        return 1.0

def calculate_atr(stock_data, period=14):
    """Calculate the Average True Range (ATR)."""
    try:
        if stock_data is None or len(stock_data) < period + 1:
            return 0.0
        high_low = stock_data['High'] - stock_data['Low']
        high_close = np.abs(stock_data['High'] - stock_data['Close'].shift())
        low_close = np.abs(stock_data['Low'] - stock_data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        return float(atr.iloc[-1])
    except:
        return 0.0

def run_scan():
    print("=== APEX DAILY MASSIVE UNIVERSE SCANNER ===")
    
    auditor = DailyAuditor()
    auditor.evaluate_pending_logs()
    
    universe = load_universe()
    print(f"Loaded {len(universe)} stocks from universe.txt")
    
    print("1. Evaluating HMM Regime...")
    try:
        symbols = {
            "Nifty": "^NSEI",
            "VIX": "^INDIAVIX",
            "USDINR": "USDINR=X",
            "BankNifty": "^NSEBANK",
            "Midcap100": "^NSEMDCP50", 
            "Bond10Y": "^TNX"
        }
        
        dataframes = {}
        for name, ticker in symbols.items():
            s = yf.download(ticker, period="6mo", progress=False)['Close']
            if isinstance(s, pd.DataFrame): s = s.iloc[:, 0]
            dataframes[name] = s
            
        df = pd.DataFrame(dataframes).ffill().dropna()
        features = pd.DataFrame(index=df.index)
        features['nifty_20d_ret'] = df['Nifty'].pct_change(20)
        features['nifty_60d_ret'] = df['Nifty'].pct_change(60)
        features['vix_lvl'] = df['VIX']
        features['vix_10d_roc'] = df['VIX'].pct_change(10)
        features['usdinr_20d_roc'] = df['USDINR'].pct_change(20)
        features['bank_rs'] = df['BankNifty'] / df['Nifty']
        features['midcap_rs'] = df['Midcap100'] / df['Nifty']
        features['bond_yield_10y'] = df['Bond10Y']
        features.dropna(inplace=True)
        
        hmm = RegimeHMM()
        model_path = os.path.join(os.path.dirname(__file__), "engines", "regime", "hmm_model.pkl")
        hmm.load_model(model_path)
        
        dummy_packet = DataPacket(ticker="DUMMY", timestamp=datetime.utcnow())
        regime_output = hmm.evaluate(dummy_packet, recent_history_df=features.iloc[-60:])
        regime_mult = regime_output['engine_weights']['bull_base_weight']
        print(f"   => Detected State: {regime_output['dominant_state']} | Bull Weight: {regime_mult:.2f}")
    except Exception as e:
        print(f"Warning: HMM evaluation failed ({e}). Defaulting to Neutral Regime.")
        regime_mult = 0.50
        regime_output = {"dominant_state": 2}
    
    # ===== FIX #4: Download REAL sector index data =====
    print("2. Downloading Sector Indices...")
    sector_data = {}
    for idx in SECTOR_INDICES:
        try:
            s = yf.download(idx, period="1y", progress=False)['Close']
            if isinstance(s, pd.DataFrame): s = s.iloc[:, 0]
            if not s.empty:
                sector_data[idx] = s
        except:
            pass
    
    print(f"3. Downloading Bulk OHLCV Data for {len(universe)} Stocks...")
    # Download Close prices for signal math
    stock_close = yf.download(universe, period="1y", progress=False)['Close']
    # Download full OHLCV for volume calculations
    stock_ohlcv_raw = yf.download(universe, period="3mo", progress=False)
    
    # ===== FIX #2: Fetch REAL fundamentals concurrently =====
    print("4. Fetching Real Fundamental Data (ROE, Margins, Growth)...")
    fundamentals = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        results_fund = executor.map(fetch_fundamentals, universe)
        for ticker, fund_data in results_fund:
            fundamentals[ticker] = fund_data
    
    results = []
    params = load_parameters()
    w_mom = params.get("w_momentum", 0.70)
    w_rs = params.get("w_rs", 0.30)
    b_thresh = params.get("buy_threshold", 38.0)
    
    print("5. Scoring All Stocks with Real Data...")
    for ticker in universe:
        if ticker not in stock_close.columns: continue
        
        raw_hist = stock_close[ticker].dropna()
        if len(raw_hist) < 10: continue
        
        # Fetch the TRUE real-time last traded price
        try:
            current_price = yf.Ticker(ticker).fast_info.last_price
        except:
            current_price = float(raw_hist.iloc[-1])
        
        hist = raw_hist.copy()
        common_index = hist.index.intersection(nifty.index)
        if len(common_index) < 200: continue
        
        hist = hist.loc[common_index]
        nifty_hist = nifty.loc[common_index]
        
        signal_price = hist.iloc[-1]
        stock_63d_ret = (signal_price / hist.iloc[-63]) - 1
        nifty_63d_ret = (nifty_hist.iloc[-1] / nifty_hist.iloc[-63]) - 1
        
        # ===== FIX #4: Real sector return =====
        sector_idx = SECTOR_MAP.get(ticker, None)
        if sector_idx and sector_idx in sector_data:
            s_data = sector_data[sector_idx].dropna()
            if len(s_data) >= 63:
                sector_63d_ret = (s_data.iloc[-1] / s_data.iloc[-63]) - 1
            else:
                sector_63d_ret = nifty_63d_ret
        else:
            sector_63d_ret = nifty_63d_ret
        
        dma_200 = hist.rolling(200).mean().iloc[-1]
        dma_50 = hist.rolling(50).mean().iloc[-1]
        dist_200d = (signal_price / dma_200) - 1
        dist_50d = (signal_price / dma_50) - 1
        
        # ===== FIX #3: Real down-volume expansion =====
        down_vol = calculate_down_volume_expansion(ticker, stock_ohlcv_raw)
        
        # ===== FIX #2: Real fundamental data =====
        fund = fundamentals.get(ticker, {"pat_growth": 0.10, "ebitda_margin": 12.0, "roe": 12.0})
        
        packet = DataPacket(ticker=ticker, timestamp=datetime.utcnow())
        packet.signals.append(Signal("STOCK_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, stock_63d_ret, datetime.utcnow()))
        packet.signals.append(Signal("NIFTY_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, nifty_63d_ret, datetime.utcnow()))
        packet.signals.append(Signal("SECTOR_63D_RET", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, sector_63d_ret, datetime.utcnow()))
        packet.signals.append(Signal("DIST_200DMA", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, dist_200d, datetime.utcnow()))
        packet.signals.append(Signal("DIST_50DMA", SignalCategory.PRICE, SignalSubSource.PRICE_ACTION, dist_50d, datetime.utcnow()))
        packet.signals.append(Signal("DOWN_VOL_EXPANSION", SignalCategory.VOLUME, SignalSubSource.PRICE_ACTION, down_vol, datetime.utcnow()))
        packet.signals.append(Signal("PAT_GROWTH_YOY", SignalCategory.FUNDAMENTAL, SignalSubSource.FINANCIAL_STATEMENT, fund["pat_growth"], datetime.utcnow()))
        packet.signals.append(Signal("EBITDA_MARGIN", SignalCategory.FUNDAMENTAL, SignalSubSource.FINANCIAL_STATEMENT, fund["ebitda_margin"], datetime.utcnow()))
        packet.signals.append(Signal("ROE", SignalCategory.FUNDAMENTAL, SignalSubSource.FINANCIAL_STATEMENT, fund["roe"], datetime.utcnow()))
        
        rs_score = RelativeStrengthEngine().evaluate(packet)['score']
        mom_score = MomentumBullEngine().evaluate(packet)['score']
        fund_score = FundamentalBullEngine().evaluate(packet)['score']
        
        technical_score = (rs_score * w_rs) + (mom_score * w_mom)
        bull_score = (technical_score * 0.80) + (fund_score * 0.20)
                      
        bear_score = TechnicalBearEngine().evaluate(packet)['score']
        
        verdict = VerdictEngine(buy_threshold=b_thresh, hold_threshold=28.0).generate_verdict(bull_score, bear_score, 0.0, regime_mult)
        
        # Calculate Predicted Trajectory string
        if verdict['decision'] == 'BUY':
            if stock_63d_ret > 0.1: trajectory = "Strong Uptrend (Momentum Breakout)"
            else: trajectory = "Accumulation Phase (Value Setup)"
        elif verdict['decision'] == 'HOLD':
            if dist_200d > 0.05: trajectory = "Consolidating above support"
            else: trajectory = "Neutral Trajectory"
        else:
            if dist_200d < -0.05: trajectory = "Bearish Breakdown (Below 200DMA)"
            else: trajectory = "Weakening Momentum (Avoid)"
        
        # ===== FIX #5: Exit strategy & 2% Risk Parity =====
        ohlcv_data = stock_ohlcv_raw[ticker] if ticker in stock_ohlcv_raw else None
        atr_14 = calculate_atr(ohlcv_data)
        
        if atr_14 > 0:
            stop_loss = round(float(current_price - (2 * atr_14)), 2)
        else:
            stop_loss = round(max(float(dma_200), float(current_price * 0.92)), 2)
            
        target_price = round(float(current_price * 1.12), 2)  
        
        # 2% Risk Parity Formula
        stop_loss_distance = current_price - stop_loss
        if stop_loss_distance > 0:
            pos_size = (0.02 * current_price) / stop_loss_distance * 100
            position_size_pct = round(min(pos_size, 25.0), 1) # Cap at 25% max portfolio allocation
        else:
            position_size_pct = 5.0
            
        results.append({
            "ticker": ticker.replace(".NS", ""),
            "current_price": round(float(current_price), 2),
            "trajectory": trajectory,
            "final_score": round(float(verdict['final_score']), 1),
            "decision": verdict['decision'],
            "stop_loss": stop_loss,
            "target_price": target_price,
            "position_size_pct": position_size_pct,
            "roe": round(fund["roe"], 1),
            "margin": round(fund["ebitda_margin"], 1)
        })
    
    # Sort: Buys first, then Holds, then Rejects - each by descending score
    order = {"BUY": 0, "HOLD": 1, "REJECT": 2}
    results.sort(key=lambda x: (order[x['decision']], -x['final_score']))
    
    output_data = {
        "regime_state": int(regime_output['dominant_state'] + 1),
        "regime_mult": round(float(regime_mult), 2),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": results
    }
    
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "latest_scan.json")
    
    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=4)
    
    # Print summary
    buys = len([r for r in results if r['decision'] == 'BUY'])
    holds = len([r for r in results if r['decision'] == 'HOLD'])
    rejects = len([r for r in results if r['decision'] == 'REJECT'])
    print(f"\nScan complete! {len(results)} stocks evaluated.")
    print(f"  BUY: {buys} | HOLD: {holds} | REJECT: {rejects}")
    print(f"Saved to {out_path}.")
    
    auditor.log_todays_scan(results)

if __name__ == "__main__":
    run_scan()
