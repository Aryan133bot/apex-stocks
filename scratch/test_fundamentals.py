import yfinance as yf
import pandas as pd

ticker = yf.Ticker("RELIANCE.NS")
try:
    inc = ticker.quarterly_income_stmt
    bs = ticker.quarterly_balance_sheet
    
    print("Income Statement columns:", inc.columns)
    print("Balance Sheet columns:", bs.columns)
    
    if not inc.empty and not bs.empty:
        # Get the most recent quarter dates
        dates = inc.columns
        for d in dates:
            net_income = inc.loc['Net Income', d] if 'Net Income' in inc.index else None
            revenue = inc.loc['Total Revenue', d] if 'Total Revenue' in inc.index else None
            equity = bs.loc['Stockholders Equity', d] if 'Stockholders Equity' in bs.index else None
            # fallback for equity
            if equity is None and 'Total Equity Gross Minority Interest' in bs.index:
                equity = bs.loc['Total Equity Gross Minority Interest', d]
            
            print(f"Date: {d}")
            print(f"  Net Income: {net_income}")
            print(f"  Revenue: {revenue}")
            print(f"  Equity: {equity}")
except Exception as e:
    print("Error:", e)
