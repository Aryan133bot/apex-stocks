import os
import pandas as pd
import yfinance as yf
import numpy as np

def fetch_decadal_data():
    print("=== DOWNLOADING 25 YEARS OF MACRO DATA (2001-2026) ===")
    
    nifty = yf.download("^NSEI", start="2001-01-01", end="2026-06-05", progress=False)['Close']
    vix = yf.download("^INDIAVIX", start="2001-01-01", end="2026-06-05", progress=False)['Close']
    
    if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
    if isinstance(vix, pd.DataFrame): vix = vix.iloc[:, 0]
    
    df = pd.DataFrame({"Nifty": nifty, "VIX": vix})
    
    # Pre-2009 VIX Synthesis (VIX didn't exist in India before ~2009)
    # We calculate the 20-day historical volatility of the Nifty to proxy it.
    df['nifty_ret'] = df['Nifty'].pct_change()
    df['hist_vol'] = df['nifty_ret'].rolling(20).std() * np.sqrt(252) * 100
    
    df['VIX_Proxy'] = df['VIX'].fillna(df['hist_vol'] * 1.1)
    
    df.dropna(subset=['Nifty', 'VIX_Proxy'], inplace=True)
    
    features = pd.DataFrame(index=df.index)
    features['nifty_20d_ret'] = df['Nifty'].pct_change(20)
    features['nifty_60d_ret'] = df['Nifty'].pct_change(60)
    features['india_vix_lvl'] = df['VIX_Proxy']
    features['india_vix_10d_roc'] = df['VIX_Proxy'].pct_change(10)
    
    # Mocking broader macro data
    features['usdinr_20d_roc'] = np.random.normal(0, 0.01, len(features))
    features['nifty500_above_200d'] = np.random.uniform(20, 80, len(features))
    features['nifty500_ad_slope'] = np.random.normal(0, 1, len(features))
    features['yield_repo_spread'] = np.random.normal(2, 0.5, len(features))
    features['fii_20d_flow'] = np.random.normal(0, 5000, len(features))
    features['bank_nifty_ratio'] = np.random.normal(2.5, 0.2, len(features))
    features['fii_dii_divergence'] = np.random.normal(0, 1000, len(features))
    
    features.dropna(inplace=True)
    
    out_dir = os.path.join(os.path.dirname(__file__), "cache")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "decadal_macro.csv")
    
    features.to_csv(out_path)
    print(f"Successfully cached {len(features)} trading days to {out_path}.")

if __name__ == "__main__":
    fetch_decadal_data()
