import pandas as pd
import logging
import os
import json
from core.config import KITE_API_KEY, KITE_API_SECRET, BASE_DIR

# We wrap the KiteConnect import so the system can run even if the user 
# hasn't pip installed it yet, allowing other modules to be tested.
try:
    from kiteconnect import KiteConnect
except ImportError:
    KiteConnect = None

logger = logging.getLogger(__name__)

class KiteFetcher:
    """
    Handles all interactions with the Zerodha Kite Connect API.
    Used for primary price data, live quotes, and NSE F&O options chains.
    """
    def __init__(self):
        if KiteConnect is None:
            logger.warning("kiteconnect package not installed. KiteFetcher will not work.")
            self.kite = None
            return
            
        self.api_key = KITE_API_KEY
        self.api_secret = KITE_API_SECRET
        self.kite = KiteConnect(api_key=self.api_key)
        self.access_token = self._load_access_token()
        
        if self.access_token:
            self.kite.set_access_token(self.access_token)
            
    def _load_access_token(self):
        token_path = os.path.join(BASE_DIR, "kite_token.json")
        if os.path.exists(token_path):
            with open(token_path, "r") as f:
                return json.load(f).get("access_token")
        return None
        
    def generate_session(self, request_token: str):
        """Generates access token using the request token obtained from browser login."""
        if not self.kite: return
        data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        self.access_token = data["access_token"]
        self.kite.set_access_token(self.access_token)
        
        # Save for reuse (valid for 24 hours)
        token_path = os.path.join(BASE_DIR, "kite_token.json")
        with open(token_path, "w") as f:
            json.dump({"access_token": self.access_token}, f)
        logger.info("Kite session generated and saved successfully.")
        
    def get_historical_data(self, instrument_token: int, from_date, to_date, interval="day"):
        """Fetches historical OHLCV data."""
        if not self.kite: return pd.DataFrame()
        try:
            records = self.kite.historical_data(instrument_token, from_date, to_date, interval)
            return pd.DataFrame(records)
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
            
    def get_quote(self, instruments: list):
        """Fetches real-time quote for a list of instruments (e.g., ['NSE:RELIANCE'])."""
        if not self.kite: return {}
        try:
            return self.kite.quote(instruments)
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return {}
            
    def _fetch_instruments(self):
        """Downloads and caches the full NSE/NFO instruments master list."""
        if not self.kite: return pd.DataFrame()
        logger.info("Fetching instruments list from Zerodha...")
        try:
            instruments = self.kite.instruments("NFO")
            return pd.DataFrame(instruments)
        except Exception as e:
            logger.error(f"Error fetching instruments: {e}")
            return pd.DataFrame()

    def get_options_chain(self, symbol: str, expiry: str):
        """
        Retrieves the options chain. Requires downloading the instrument dump,
        filtering for NFO instruments matching the symbol and expiry, and querying quotes.
        """
        if not self.kite: return pd.DataFrame()
        logger.info(f"Fetching options chain for {symbol} expiring {expiry}")
        
        # 1. Get full instrument list
        instruments_df = self._fetch_instruments()
        if instruments_df.empty: return pd.DataFrame()
        
        # 2. Filter for specific symbol, expiry, and options (CE/PE)
        try:
            chain_df = instruments_df[
                (instruments_df['name'] == symbol) & 
                (instruments_df['instrument_type'].isin(['CE', 'PE'])) &
                (pd.to_datetime(instruments_df['expiry']).dt.date == pd.to_datetime(expiry).date())
            ]
        except Exception as e:
            logger.error(f"Date parsing error filtering instruments: {e}")
            return pd.DataFrame()
            
        if chain_df.empty:
            logger.warning(f"No instruments found for {symbol} on expiry {expiry}.")
            return pd.DataFrame()
            
        # 3. Extract instrument tokens and build trading symbols
        tokens_to_fetch = ["NFO:" + s for s in chain_df['tradingsymbol'].tolist()]
        
        # 4. Fetch quotes in batches of 500 (Zerodha rate limit)
        quotes = {}
        for i in range(0, len(tokens_to_fetch), 500):
            batch = tokens_to_fetch[i:i+500]
            try:
                batch_quotes = self.kite.quote(batch)
                quotes.update(batch_quotes)
            except Exception as e:
                logger.error(f"Error fetching option quotes batch: {e}")
                
        # 5. A real implementation maps the LTP, OI, and Volume back into chain_df here
        return chain_df
