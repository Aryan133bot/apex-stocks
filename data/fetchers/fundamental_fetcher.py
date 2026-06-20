import requests
import json
import time
import os
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
import json
import time
import os
import sqlite3
from datetime import datetime, timedelta

CACHE_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fundamentals_cache.db")

class FundamentalFetcher:
    def __init__(self, cache_days=7):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.screener.in",
            "Accept": "application/json"
        }
        self.cache_days = cache_days
        self._init_cache()
        
    def _init_cache(self):
        conn = sqlite3.connect(CACHE_DB)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS screener_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT,
                last_updated TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def get_fundamentals(self, symbol, use_cache=True):
        """Fetches fundamental data from Screener.in with local SQLite caching."""
        if use_cache:
            conn = sqlite3.connect(CACHE_DB)
            row = conn.execute("SELECT data_json, last_updated FROM screener_cache WHERE ticker = ?", (symbol,)).fetchone()
            conn.close()
            
            if row:
                last_updated = datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
                if datetime.now() - last_updated < timedelta(days=self.cache_days):
                    return json.loads(row[0])
        
        # Rate limiting adherence
        time.sleep(2.0)
        
        url = f"https://www.screener.in/api/company/{symbol}/"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                
                # Update Cache
                conn = sqlite3.connect(CACHE_DB)
                conn.execute('''
                    INSERT OR REPLACE INTO screener_cache (ticker, data_json, last_updated)
                    VALUES (?, ?, ?)
                ''', (symbol, json.dumps(data), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                
                return data
            else:
                print(f"[FundamentalFetcher] Screener.in HTTP {resp.status_code}. Using yfinance fallback for {symbol}")
                return self._fetch_yf_fallback(symbol)
        except Exception as e:
            print(f"[FundamentalFetcher] Exception fetching {symbol}: {e}. Using yfinance fallback.")
            return self._fetch_yf_fallback(symbol)

    def _fetch_yf_fallback(self, symbol):
        yf_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            q_fin = ticker.quarterly_financials
            pat_history = []
            if not q_fin.empty and "Net Income" in q_fin.index:
                # Get the last 4 quarters, oldest first (so we reverse it)
                pat_history = [float(x) for x in q_fin.loc["Net Income"].dropna().head(4).values[::-1]]
                
            return {"source": "yfinance", "info": info, "pat_history": pat_history}
        except Exception as e:
            print(f"YF Fallback failed for {yf_symbol}: {e}")
            return None

    def parse_quality_metrics(self, data):
        """Extracts Gate 0 required metrics from the JSON."""
        if not data:
            return None
            
        if "source" in data and data["source"] == "yfinance":
            info = data.get("info", {})
            return {
                "ttm_revenue": info.get('totalRevenue', 0.0),
                "debt_to_equity": info.get('debtToEquity', 0.0) / 100.0 if info.get('debtToEquity') else 0.0,
                "pat_history": data.get("pat_history", []),
                "pe_ratio": info.get('trailingPE', 0.0)
            }
            
        try:
            # Note: The exact JSON structure of Screener.in's internal API can vary.
            # This is a safe parsing attempt. We fallback to None if keys are missing.
            ratios = data.get('ratios', {})
            profit_loss = data.get('profit_loss', {})
            
            # Get latest TTM Revenue
            ttm_revenue = None
            if 'sales' in profit_loss and len(profit_loss['sales']) > 0:
                ttm_revenue = profit_loss['sales'][-1]
                
            # Get Debt to Equity
            debt_to_equity = ratios.get('debt_to_equity', None)
            
            # Get latest Quarters PAT
            quarters = data.get('quarters', {})
            pat_history = []
            if 'net_profit' in quarters:
                pat_history = quarters['net_profit'][-4:] # Last 4 quarters
                
            return {
                "ttm_revenue": float(ttm_revenue) if ttm_revenue else 0.0,
                "debt_to_equity": float(debt_to_equity) if debt_to_equity is not None else 0.0,
                "pat_history": pat_history,
                "pe_ratio": float(ratios.get('pe', 0.0))
            }
        except Exception as e:
            print(f"[FundamentalFetcher] Error parsing metrics: {e}")
            return None

if __name__ == "__main__":
    fetcher = FundamentalFetcher()
    data = fetcher.get_fundamentals("RELIANCE", use_cache=False)
    if data:
        metrics = fetcher.parse_quality_metrics(data)
        print("Reliance Metrics:", metrics)
