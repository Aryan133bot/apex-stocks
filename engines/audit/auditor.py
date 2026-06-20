import os
import sys
import yfinance as yf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from data.store import get_db_connection

class DailyAuditor:
    def __init__(self):
        pass
        
    def evaluate_pending_logs(self):
        """Finds PENDING logs from previous days, fetches current prices, and grades them."""
        print("[AUDITOR] Evaluating previous days' recommendations...")
        conn = get_db_connection()
        pending_records = conn.execute("SELECT * FROM daily_audit_log WHERE status = 'PENDING'").fetchall()
        
        if not pending_records:
            print("[AUDITOR] No pending recommendations to evaluate.")
            conn.close()
            return
            
        tickers = list(set([r['ticker'] for r in pending_records]))
        live_prices = {}
        
        def fetch_price(t):
            try:
                return t, yf.Ticker(t + ".NS").fast_info.last_price
            except:
                return t, None
                
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_price, tickers)
            for t, p in results:
                if p is not None:
                    live_prices[t] = p
                    
        evaluated_count = 0
        correct_count = 0
                    
        for row in pending_records:
            ticker = row['ticker']
            if ticker not in live_prices: continue
            
            next_day_price = live_prices[ticker]
            start_price = row['start_price']
            recommendation = row['recommendation']
            
            pnl_pct = ((next_day_price / start_price) - 1) * 100 if start_price > 0 else 0
            
            was_correct = 0
            if recommendation == "BUY" and pnl_pct > 0:
                was_correct = 1
            elif recommendation == "REJECT" and pnl_pct < 0:
                was_correct = 1
            elif recommendation == "HOLD" and (-1.5 <= pnl_pct <= 1.5):
                was_correct = 1
                
            conn.execute('''
                UPDATE daily_audit_log 
                SET next_day_price = ?, outcome_pnl_pct = ?, was_correct = ?, status = 'EVALUATED'
                WHERE id = ?
            ''', (next_day_price, pnl_pct, was_correct, row['id']))
            
            evaluated_count += 1
            if was_correct:
                correct_count += 1
                
        conn.commit()
        conn.close()
        
        if evaluated_count > 0:
            win_rate = (correct_count / evaluated_count) * 100
            print(f"[AUDITOR] Evaluated {evaluated_count} trades. Win Rate: {win_rate:.1f}%")
        
    def log_todays_scan(self, scan_results):
        """Saves today's scan results as PENDING."""
        print("[AUDITOR] Archiving today's recommendations...")
        conn = get_db_connection()
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        count = 0
        for stock in scan_results:
            conn.execute('''
                INSERT INTO daily_audit_log 
                (scan_date, ticker, recommendation, start_price, target_price, stop_loss, status)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
            ''', (
                date_str,
                stock['ticker'],
                stock['decision'],
                stock['current_price'],
                stock.get('target_price'),
                stock.get('stop_loss'),
            ))
            count += 1
            
        conn.commit()
        conn.close()
        print(f"[AUDITOR] Successfully archived {count} recommendations for future evaluation.")
