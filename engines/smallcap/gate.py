class SmallCapGate:
    def __init__(self):
        pass

    def run_gate_zero(self, metrics, promoter_holding, avg_turnover_20d, today_turnover):
        """
        Executes Gate 0 (Quality Filter) - Hard Rules.
        Returns (True, "Passed") or (False, "Reason for failure")
        """
        if not metrics:
            return False, "Failed Gate 0: Missing Fundamental Metrics"
            
        # Q1: Revenue positive
        if metrics.get('ttm_revenue', 0) <= 0:
            return False, "Failed Q1: Revenue <= 0"
            
        # Q2: Not in persistent loss
        pat_history = metrics.get('pat_history', [])
        if pat_history and len(pat_history) >= 4:
            positive_quarters = sum(1 for p in pat_history if p > 0)
            if positive_quarters < 2:
                return False, "Failed Q2: Persistent Loss (>2 negative quarters in last 4)"
                
        # Q3: Debt Manageable (Relaxed to 10.0 for capital-heavy small caps like railways)
        if metrics.get('debt_to_equity', 0) > 10.0:
            return False, "Failed Q3: Debt/Equity > 10.0"
            
        # Q4: Promoter Holding
        if promoter_holding < 30.0:
            return False, f"Failed Q4: Promoter Holding < 30% ({promoter_holding:.1f}%)"
            
        # Q7: Liquidity Floor
        if avg_turnover_20d < 20_000_000: # Rs 2 crore
            return False, f"Failed Q7: 20D Avg Turnover < 2 Cr (Rs.{avg_turnover_20d:,.0f})"
            
            
        return True, "Passed Gate 0"
        
    def run_manipulation_screen(self, ohlcv_data, metrics, pledged_pct):
        """
        Flags operator-driven stocks.
        Returns (True, "Clean") or (False, "Manipulation Flag Triggered")
        """
        if ohlcv_data is None or len(ohlcv_data) < 20:
            return False, "Insufficient data for Manipulation Screen"
            
        if not metrics:
            return False, "Missing metrics for Manipulation Screen"
            
        recent = ohlcv_data.iloc[-1]
        hist_20d = ohlcv_data.tail(20)
        
        try:
            avg_vol_20d = float(hist_20d['Volume'].mean().squeeze())
            today_vol = float(recent['Volume'].squeeze())
            r_close = float(recent['Close'].squeeze())
            r_open = float(recent['Open'].squeeze())
        except Exception:
            avg_vol_20d = float(hist_20d['Volume'].mean().iloc[0])
            today_vol = float(recent['Volume'].iloc[0])
            r_close = float(recent['Close'].iloc[0])
            r_open = float(recent['Open'].iloc[0])
            
        today_price_move = ((r_close - r_open) / r_open) * 100 if r_open > 0 else 0
        
        # M1: Volume-Price Anomaly
        if avg_vol_20d > 0 and today_vol > (10 * avg_vol_20d) and today_price_move > 8.0:
            return False, "Flag M1: Extreme Volume-Price Anomaly (Pump Signature)"
            
        # M2: Circuit Cluster
        # Define upper circuit as a day where High == Close and move > 4.5%
        circuit_count = 0
        last_10d = ohlcv_data.tail(10)
        for _, row in last_10d.iterrows():
            try:
                row_open = float(row['Open'].squeeze())
                row_close = float(row['Close'].squeeze())
                row_high = float(row['High'].squeeze())
            except Exception:
                row_open = float(row['Open'].iloc[0])
                row_close = float(row['Close'].iloc[0])
                row_high = float(row['High'].iloc[0])
                
            if row_open > 0:
                move = ((row_close - row_open) / row_open) * 100
                if move > 4.5 and abs(row_high - row_close) < (row_close * 0.005):
                    circuit_count += 1
                
        if circuit_count >= 3:
            return False, f"Flag M2: Circuit Cluster ({circuit_count} circuits in 10 days)"
            
        # M3: Promoter Pledge + Volume Spike
        if pledged_pct > 40.0:
            try:
                vol_5d = float(ohlcv_data.tail(5)['Volume'].mean().squeeze())
            except Exception:
                vol_5d = float(ohlcv_data.tail(5)['Volume'].mean().iloc[0])
                
            if avg_vol_20d > 0 and vol_5d > (5 * avg_vol_20d):
                return False, "Flag M3: High Pledge + Volume Spike"
                
        # M5: Extreme PE Divergence
        if metrics.get('pe_ratio', 0) > 100 and metrics.get('ttm_revenue', 0) < 40_000_000: # 40 Cr TTM = ~10Cr/quarter
            return False, "Flag M5: Price-to-Fundamentals Extreme Divergence"
            
        return True, "Clean"
