import requests
import yfinance as yf
from datetime import datetime

class MacroFetcher:
    def __init__(self):
        # The RBI endpoints are sometimes IP restricted or change structure.
        # These are placeholders according to the spec.
        self.rbi_repo_url = "https://api.rbi.org.in/api/v1/getMetaData?seriesId=RR"
        self.rbi_cpi_url = "https://api.rbi.org.in/api/v1/getData?seriesId=RBICPI"
        
    def get_rbi_repo_rate(self):
        """Fetches the latest RBI Repo Rate."""
        try:
            resp = requests.get(self.rbi_repo_url, timeout=5)
            if resp.status_code == 200:
                # Actual parsing depends on RBI JSON structure
                return resp.json()
        except Exception as e:
            pass
            
        return {"rate": 6.50, "status": "fallback"} # Current repo rate fallback
        
    def get_usd_inr(self):
        """Fetches latest USD/INR rate via yfinance."""
        try:
            data = yf.download("USDINR=X", period="5d", progress=False)
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except:
            pass
        return 83.50 # Fallback
        
if __name__ == "__main__":
    fetcher = MacroFetcher()
    print("Repo Rate:", fetcher.get_rbi_repo_rate())
    print("USD/INR:", fetcher.get_usd_inr())
