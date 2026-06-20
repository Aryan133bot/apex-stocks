class PatternClassifier:
    def classify(self, ohlcv_data, metrics, promoter_holding):
        """
        Classifies a stock into Pattern 1, 2, or 3 based on hard data.
        Returns ("PATTERN X", score) or (None, 0)
        """
        if ohlcv_data is None or len(ohlcv_data) < 250:
            return None, 0
            
        recent = ohlcv_data.iloc[-1]
        hist_20d = ohlcv_data.tail(20)
        hist_5d = ohlcv_data.tail(5)
        
        try:
            avg_vol_20d = float(hist_20d['Volume'].mean().squeeze())
            avg_vol_5d = float(hist_5d['Volume'].mean().squeeze())
            high_52w = float(ohlcv_data.tail(250)['High'].max().squeeze())
            low_52w = float(ohlcv_data.tail(250)['Low'].min().squeeze())
            current_price = float(recent['Close'].squeeze())
        except Exception:
            avg_vol_20d = float(hist_20d['Volume'].mean().iloc[0])
            avg_vol_5d = float(hist_5d['Volume'].mean().iloc[0])
            high_52w = float(ohlcv_data.tail(250)['High'].max().iloc[0])
            low_52w = float(ohlcv_data.tail(250)['Low'].min().iloc[0])
            current_price = float(recent['Close'].iloc[0])
        
        # PATTERN 3: 52-Week Low Reversal with Volume
        # Trigger conditions: Price within 15% of 52W low, Vol 5D > 2x 20D avg
        dist_from_low_pct = ((current_price - low_52w) / low_52w) * 100
        if dist_from_low_pct <= 15.0 and avg_vol_5d > (2 * avg_vol_20d):
            # Calculate Score
            vol_score = 90 if avg_vol_5d > (3*avg_vol_20d) else 70 if avg_vol_5d > (2*avg_vol_20d) else 50
            price_score = 90 if dist_from_low_pct <= 5.0 else 70 if dist_from_low_pct <= 10.0 else 50
            
            # Fundamental health proxy
            debt_eq = metrics.get('debt_to_equity', 0)
            fund_score = 100 if debt_eq < 0.5 else 50 if debt_eq < 1.0 else 20
            
            final_score = (vol_score * 0.35) + (price_score * 0.25) + (fund_score * 0.25) + (80 * 0.15) # 80 is news silence proxy
            if final_score >= 62:
                return "PATTERN 3 - LOW REVERSAL", final_score
                
        # PATTERN 1: Earnings-Driven Re-Rating (Approximation using proxy metrics if no quarterly data)
        # Assuming PAT history exists from yfinance:
        pat_history = metrics.get('pat_history', [])
        if len(pat_history) >= 2:
            q_n = pat_history[0]
            q_n_1 = pat_history[1]
            if q_n > 0 and q_n_1 > 0 and q_n > (q_n_1 * 1.10): # 10% QoQ growth
                if metrics.get('pe_ratio', 100) < 30: # Cheap proxy
                    
                    e1_score = 90 if q_n > (q_n_1 * 1.20) else 70
                    e2_score = 75 # Revenue growth proxy
                    e3_score = 90 if metrics.get('pe_ratio', 100) < 15 else 55
                    
                    final_score = (e1_score * 0.35) + (e2_score * 0.30) + (e3_score * 0.25) + (0 * 0.10)
                    if final_score >= 65:
                        return "PATTERN 1 - EARNINGS", final_score
                        
        # PATTERN 2: Sector Tailwind + Low Float
        # Trigger: Promoter holding > 60% (Low float) and Volume increasing
        if promoter_holding > 60.0 and avg_vol_5d > (1.5 * avg_vol_20d):
            s1_score = 60 # Sector proxy
            s2_score = 50 # Laggard proxy
            s3_score = 90 if promoter_holding > 70 else 70 if promoter_holding > 60 else 55
            s4_score = 90 if avg_vol_5d > (2.5 * avg_vol_20d) else 70
            
            final_score = (s1_score * 0.30) + (s2_score * 0.25) + (s3_score * 0.25) + (s4_score * 0.20)
            if final_score >= 60:
                return "PATTERN 2 - SECTOR + FLOAT", final_score
                
        # PATTERN 4: True Momentum Breakout (Decadal Winner)
        # Trigger: Price within 5% of 52W High, Volume spikes 1.5x
        dist_from_high_pct = ((high_52w - current_price) / high_52w) * 100
        if dist_from_high_pct <= 10.0 and avg_vol_5d > (1.2 * avg_vol_20d):
            # Calculate Score
            vol_score = 90 if avg_vol_5d > (2*avg_vol_20d) else 75
            price_score = 95 if dist_from_high_pct <= 2.0 else 80 if dist_from_high_pct <= 5.0 else 65
            
            final_score = (vol_score * 0.40) + (price_score * 0.60)
            if final_score >= 65:
                return "PATTERN 4 - MOMENTUM BREAKOUT", final_score
                
        return None, 0
