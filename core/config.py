import os

# Trading Universe & Limits
UNIVERSE = "NIFTY500"          # Trading universe
BROKER = "ZERODHA"             # Broker
MIN_MARKET_CAP_CR = 1000       # ₹1,000 crore minimum
MIN_ADV_CR = 5                 # ₹5 crore average daily volume
MAX_POSITIONS = 6              # Maximum simultaneous open positions
RISK_PER_TRADE_PCT = 0.015     # 1.5% portfolio risk per trade
CASH_RESERVE_PCT = 0.20        # Always keep 20% in cash
MIN_RR_RATIO = 2.0             # Minimum reward:risk ratio
NET_EDGE_THRESHOLD = 22        # Minimum Net Edge to approve trade

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
DB_PATH = os.path.join(BASE_DIR, "apex_data.db")

# API Keys (To be filled in local config.yaml or env vars)
KITE_API_KEY = os.environ.get("KITE_API_KEY", "")
KITE_API_SECRET = os.environ.get("KITE_API_SECRET", "")
