import os
import pickle
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engines.regime.hmm_model import RegimeHMM

def fetch_macro_data(start_date="2010-01-01"):
    print(f"Fetching Macro Data from {start_date}...")
    
    # Reliable macro proxies available freely via yfinance
    symbols = {
        "Nifty": "^NSEI",
        "VIX": "^INDIAVIX",
        "USDINR": "USDINR=X",
        "BankNifty": "^NSEBANK",
        "Midcap100": "^NSEMDCP50", 
        "Bond10Y": "^TNX"
    }
    
    dataframes = {}
    for name, ticker in symbols.items():
        try:
            print(f"  Downloading {name} ({ticker})...")
            df = yf.download(ticker, start=start_date, progress=False)['Close']
            if isinstance(df, pd.DataFrame):
                df = df.iloc[:, 0]
            dataframes[name] = df
        except Exception as e:
            print(f"  Warning: Failed to download {name} ({ticker}) - {e}")
            
    print("Aligning and formatting dataframe...")
    df = pd.DataFrame(dataframes)
    df.ffill(inplace=True)
    df.dropna(inplace=True)
    
    return df

def generate_hmm_features(df):
    """
    Generates the 8 robust macro features for the HMM.
    """
    print("Generating HMM macro features...")
    features = pd.DataFrame(index=df.index)
    
    # Core Return/Trend
    features['nifty_20d_ret'] = df['Nifty'].pct_change(20)
    features['nifty_60d_ret'] = df['Nifty'].pct_change(60)
    
    # Volatility & Fear
    features['vix_lvl'] = df['VIX']
    features['vix_10d_roc'] = df['VIX'].pct_change(10)
    
    # Currency Stress
    features['usdinr_20d_roc'] = df['USDINR'].pct_change(20)
    
    # Financial Sector Health
    features['bank_rs'] = df['BankNifty'] / df['Nifty']
    
    # Market Breadth Proxy (Midcaps vs Large Caps)
    features['midcap_rs'] = df['Midcap100'] / df['Nifty']
    
    # Cost of Capital / Yield Spread
    features['bond_yield_10y'] = df['Bond10Y']
    
    features.dropna(inplace=True)
    return features

def train_and_save_hmm():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(output_dir, "hmm_model.pkl")
    
    df = fetch_macro_data(start_date="2010-01-01")
    features = generate_hmm_features(df)
    
    print(f"Training dataset size: {len(features)} days")
    print("Training the Gaussian HMM (100 EM iterations)...")
    
    hmm = RegimeHMM()
    hmm.train(features)
    
    print("Model Training Complete. Latent State Mapping (Lower Index = Bullish):")
    print(hmm.state_map)
    
    with open(model_path, 'wb') as f:
        pickle.dump({
            "model": hmm.model,
            "scaler": hmm.scaler,
            "state_map": hmm.state_map,
            "trained_features": features.columns.tolist()
        }, f)
        
    print(f"Model successfully saved to {model_path}")

if __name__ == "__main__":
    train_and_save_hmm()
