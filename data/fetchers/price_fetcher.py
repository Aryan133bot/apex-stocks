import os
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

# Attempt to import jugaad_data
try:
    from jugaad_data.nse import bhavcopy_save
    JUGAAD_AVAILABLE = True
except ImportError:
    JUGAAD_AVAILABLE = False

class PriceFetcher:
    def __init__(self, output_dir="./data/cache"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def get_latest_bhavcopy(self, max_days_back=5):
        """Attempts to download the most recent trading day's bhavcopy using jugaad-data."""
        if not JUGAAD_AVAILABLE:
            print("[PriceFetcher] jugaad-data not installed. Please pip install jugaad-data.")
            return None
            
        today = datetime.now()
        
        for i in range(max_days_back):
            check_date = today - timedelta(days=i)
            # Skip weekends
            if check_date.weekday() > 4:
                continue
                
            try:
                # Returns path to downloaded CSV
                file_path = bhavcopy_save(check_date.date(), self.output_dir)
                print(f"[PriceFetcher] Successfully downloaded Bhavcopy for {check_date.date()}")
                
                df = pd.read_csv(file_path)
                
                # Check for new NSE format headers vs old format
                if 'SctySrs' in df.columns:
                    df = df[df['SctySrs'] == 'EQ']
                    df = df.rename(columns={
                        'TckrSymb': 'SYMBOL',
                        'OpnPric': 'Open',
                        'HghPric': 'High',
                        'LwPric': 'Low',
                        'ClsPric': 'Close',
                        'TtlTradgVol': 'Volume'
                    })
                elif 'SERIES' in df.columns:
                    df = df[df['SERIES'] == 'EQ']
                    df = df.rename(columns={
                        'OPEN': 'Open',
                        'HIGH': 'High',
                        'LOW': 'Low',
                        'CLOSE': 'Close',
                        'TOTTRDQTY': 'Volume'
                    })
                    
                return df
            except Exception as e:
                print(f"[PriceFetcher] Exception on {check_date.date()}: {e}")
                pass
                
        print(f"[PriceFetcher] Failed to find Bhavcopy in the last {max_days_back} days.")
        return None
        
    def get_historical_data(self, ticker, period="1y"):
        """Fallback to yfinance for historical OHLCV data."""
        # Ensure NSE suffix
        symbol = ticker if ticker.endswith(".NS") else f"{ticker}.NS"
        try:
            data = yf.download(symbol, period=period, progress=False)
            return data
        except Exception as e:
            print(f"[PriceFetcher] Failed to download {symbol} via yfinance: {e}")
            return None
            
    def get_bulk_historical_data(self, tickers, period="3mo"):
        """Downloads bulk historical data via yfinance for multiple tickers."""
        symbols = [t if t.endswith(".NS") else f"{t}.NS" for t in tickers]
        try:
            data = yf.download(symbols, period=period, progress=False)
            return data
        except Exception as e:
            print(f"[PriceFetcher] Failed to download bulk data: {e}")
            return None

if __name__ == "__main__":
    fetcher = PriceFetcher()
    bhav = fetcher.get_latest_bhavcopy()
    if bhav is not None:
        print(f"Bhavcopy loaded with {len(bhav)} stocks.")
    else:
        print("Bhavcopy fetch failed or library missing. Testing yfinance fallback...")
        hist = fetcher.get_historical_data("RELIANCE")
        print(f"Reliance historical data points: {len(hist)}")
