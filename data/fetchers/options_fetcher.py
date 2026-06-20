import os

try:
    from breeze_connect import BreezeConnect
    BREEZE_AVAILABLE = True
except ImportError:
    BREEZE_AVAILABLE = False

class OptionsFetcher:
    def __init__(self):
        self.api_key = os.environ.get("BREEZE_API_KEY", "")
        self.api_secret = os.environ.get("BREEZE_API_SECRET", "")
        self.session_token = os.environ.get("BREEZE_SESSION_TOKEN", "")
        
        self.breeze = None
        if BREEZE_AVAILABLE and self.api_key and self.api_secret:
            try:
                self.breeze = BreezeConnect(api_key=self.api_key)
                self.breeze.generate_session(api_secret=self.api_secret, session_token=self.session_token)
            except Exception as e:
                print(f"[OptionsFetcher] Failed to connect to ICICI Breeze: {e}")
                self.breeze = None

    def get_option_chain(self, ticker, expiry_date):
        """Fetches full option chain (OI, Volume, IV) for a given ticker and expiry."""
        if self.breeze:
            try:
                chain = self.breeze.get_option_chain_quotes(
                    stock_code=ticker,
                    exchange_code="NFO",
                    product_type="options",
                    right="call", # Can fetch both
                    expiry_date=expiry_date
                )
                return chain
            except Exception as e:
                print(f"[OptionsFetcher] Error fetching option chain for {ticker}: {e}")
                return None
                
        # Mock Fallback if not connected
        return self._mock_option_chain(ticker)
        
    def _mock_option_chain(self, ticker):
        """Fallback for when ICICI Breeze is not configured."""
        return {
            "status": "Mock",
            "message": "Breeze API not configured.",
            "data": [
                {"strike_price": 100, "open_interest": 50000, "implied_volatility": 18.5},
                {"strike_price": 105, "open_interest": 75000, "implied_volatility": 22.1}
            ]
        }

if __name__ == "__main__":
    fetcher = OptionsFetcher()
    chain = fetcher.get_option_chain("NIFTY", "2025-07-31T06:00:00.000Z")
    print("Options Chain Result:", chain)
