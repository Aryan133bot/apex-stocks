import os
import json
from datetime import datetime
from data.fetchers.price_fetcher import PriceFetcher
from data.fetchers.fundamental_fetcher import FundamentalFetcher
from data.fetchers.shareholding_fetcher import ShareholdingFetcher
from engines.smallcap.gate import SmallCapGate
from engines.smallcap.patterns import PatternClassifier
from engines.smallcap.liquidity import SmallCapLiquidity

def get_universe():
    universe_path = os.path.join(os.path.dirname(__file__), 'data', 'universe.txt')
    if os.path.exists(universe_path):
        with open(universe_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return ["SUZLON.NS", "IRFC.NS", "RVNL.NS", "MAZDOCK.NS"] # Fallback

def run_smallcap_module():
    print("=== APEX SMALL-CAP MOMENTUM QUALITY MODULE ===")
    
    price_fetcher = PriceFetcher()
    fund_fetcher = FundamentalFetcher()
    share_fetcher = ShareholdingFetcher()
    
    gate = SmallCapGate()
    classifier = PatternClassifier()
    liquidity_engine = SmallCapLiquidity(portfolio_capital=100000)
    
    results = []
    
    print("1. Fetching Latest Market Data...")
    universe = get_universe()
    ohlcv_dict = {}
    for ticker in universe:
        df = price_fetcher.get_historical_data(ticker, period="1y")
        if df is not None and not df.empty:
            ohlcv_dict[ticker] = df
            
    print("2. Running Small-Cap Candidates Through Quality Gates...")
    for ticker, ohlcv in ohlcv_dict.items():
        try:
            try:
                current_price = float(ohlcv['Close'].squeeze().iloc[-1])
            except TypeError:
                current_price = float(ohlcv['Close'].iloc[-1].iloc[0])
            
            if not (10 <= current_price <= 50000):
                print(f"[{ticker}] Rejected: Price {current_price} out of range.")
                continue
                
            raw_fundamentals = fund_fetcher.get_fundamentals(ticker, use_cache=True)
            metrics = fund_fetcher.parse_quality_metrics(raw_fundamentals)
            
            promoter_holding = share_fetcher.get_promoter_holding(ticker)
            pledge_pct = share_fetcher.get_pledged_data(ticker)
            
            hist_20d = ohlcv.tail(20)
            try:
                avg_vol_20d = float(hist_20d['Volume'].squeeze().mean())
                today_vol = float(ohlcv['Volume'].squeeze().iloc[-1])
            except TypeError:
                avg_vol_20d = float(hist_20d['Volume'].mean().iloc[0])
                today_vol = float(ohlcv['Volume'].iloc[-1].iloc[0])
            
            avg_turnover_20d = avg_vol_20d * current_price
            today_turnover = today_vol * current_price
            
            # GATE 0
            gate_pass, gate_msg = gate.run_gate_zero(metrics, promoter_holding, avg_turnover_20d, today_turnover)
            if not gate_pass:
                print(f"[{ticker}] Rejected by Gate 0: {gate_msg}")
                continue
                
            # MANIPULATION SCREEN
            manip_clean, manip_msg = gate.run_manipulation_screen(ohlcv, metrics, pledge_pct)
            if not manip_clean:
                print(f"[{ticker}] Rejected by Manipulation Screen: {manip_msg}")
                continue
                
            # PATTERN CLASSIFIER
            pattern_type, pattern_score = classifier.classify(ohlcv, metrics, promoter_holding)
            if pattern_type is None:
                print(f"[{ticker}] Rejected: No pattern matched.")
                continue
                
            # LIQUIDITY ENGINE
            liq_data = liquidity_engine.calculate_exit_safety(0, avg_turnover_20d, pattern_type)
            if liq_data['status'] == 'REJECT':
                print(f"[{ticker}] Rejected by Liquidity Engine.")
                continue
                
            print(f"[{ticker}] PASSED! Pattern: {pattern_type} | Score: {pattern_score:.1f}")
            results.append({
                "ticker": ticker,
                "current_price": round(current_price, 2),
                "pattern": pattern_type,
                "score": round(pattern_score, 1),
                "status": liq_data['status'],
                "liquidity_ratio": liq_data['exit_liquidity_ratio'],
                "position_size": liq_data['final_position'],
                "max_holding_days": liq_data['max_holding_days']
            })
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            
    print(f"\nScan complete. Found {len(results)} valid candidates passing all gates.")
    
    # Save the scan file directly to output/ or web/static/ so it's easily loadable
    os.makedirs(os.path.join(os.path.dirname(__file__), 'output'), exist_ok=True)
    output_path = os.path.join(os.path.dirname(__file__), 'output', 'smallcap_scan.json')
    with open(output_path, 'w') as f:
        json.dump({
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "candidates": results
        }, f, indent=4)
        
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    run_smallcap_module()
