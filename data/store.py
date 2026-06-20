import sqlite3
import os
import logging
from core.config import DB_PATH

logger = logging.getLogger(__name__)

def get_db_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Creates the necessary tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Prices table (Daily OHLCV)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (symbol, date)
        )
    ''')
    
    # Fundamentals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fundamentals (
            symbol TEXT,
            quarter TEXT,
            revenue REAL,
            ebitda REAL,
            pat REAL,
            eps REAL,
            debt REAL,
            cash REAL,
            equity REAL,
            pe REAL,
            pb REAL,
            roe REAL,
            roce REAL,
            PRIMARY KEY (symbol, quarter)
        )
    ''')
    
    # Signals table (Daily signal scores per stock)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            symbol TEXT,
            date TEXT,
            bull_score REAL,
            bear_score REAL,
            uncertainty_score REAL,
            net_edge REAL,
            PRIMARY KEY (symbol, date)
        )
    ''')
    
    # Trades table (Log of all paper/live trades)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            entry_date TEXT,
            entry_price REAL,
            shares INTEGER,
            stop_loss REAL,
            target REAL,
            status TEXT,
            exit_date TEXT,
            exit_price REAL,
            pnl REAL
        )
    ''')
    
    # FII/DII flow
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fii_dii_flow (
            date TEXT PRIMARY KEY,
            fii_net_equity REAL,
            dii_net_equity REAL
        )
    ''')
    
    # Bulk deals
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bulk_deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            client_name TEXT,
            symbol TEXT,
            action TEXT,
            quantity INTEGER,
            price REAL
        )
    ''')
    
    # Promoter data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promoter_data (
            symbol TEXT,
            quarter TEXT,
            holding_pct REAL,
            pledge_pct REAL,
            PRIMARY KEY (symbol, quarter)
        )
    ''')
    
    # Events calendar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            event_date TEXT,
            affected_sectors TEXT,
            impact_score REAL
        )
    ''')

    # Regime History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regime_history (
            date TEXT PRIMARY KEY,
            s1_prob REAL,
            s2_prob REAL,
            s3_prob REAL,
            s4_prob REAL,
            s5_prob REAL,
            dominant_state INTEGER
        )
    ''')
    
    # Portfolio Tracker
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            buy_price REAL,
            quantity INTEGER,
            term_category TEXT,
            date_added TEXT
        )
    ''')
    
    # Daily Audit Log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date TEXT,
            ticker TEXT,
            recommendation TEXT,
            start_price REAL,
            target_price REAL,
            stop_loss REAL,
            next_day_price REAL,
            outcome_pnl_pct REAL,
            was_correct INTEGER,
            status TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Database successfully initialized at {DB_PATH}")

def get_portfolio():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM portfolio").fetchall()
    conn.close()
    return [dict(ix) for ix in items]

def add_portfolio_position(ticker: str, buy_price: float, quantity: int, term_category: str, date_added: str):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO portfolio (ticker, buy_price, quantity, term_category, date_added) VALUES (?, ?, ?, ?, ?)",
        (ticker, buy_price, quantity, term_category, date_added)
    )
    conn.commit()
    conn.close()

def remove_portfolio_position(position_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM portfolio WHERE id = ?", (position_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Ensure reports directory exists
    from core.config import REPORT_OUTPUT_DIR
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    
    # Initialize the database
    initialize_database()
