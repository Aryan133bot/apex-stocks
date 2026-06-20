import datetime
import math
from typing import Dict
from core.types import Signal, SignalCategory

# Half-lives mapped to lambda decay constants (λ = ln(2) / half_life)
DECAY_CONSTANTS = {
    SignalCategory.PRICE: 0.693,           # 1 hr half-life (tick/intraday)
    SignalCategory.OPTIONS: 0.050,         # 14 hrs
    SignalCategory.SENTIMENT: 0.099,       # 7 hrs
    SignalCategory.FUNDAMENTAL: 0.0023,    # 300 hrs (12.5 days)
    SignalCategory.INSTITUTIONAL: 0.00048, # 1440 hrs (60 days) for 13F trend
    SignalCategory.MACRO: 0.0010           # 700 hrs (29 days)
}

SOURCE_RELIABILITY = {
    "polygon": 1.00,
    "fred": 1.00,
    "fmp": 0.90,
    "quiver": 0.88,
    "finnhub": 0.82,
    "alpaca": 0.95,
    "yfinance": 0.70,
    "alpha_vantage": 0.68,
    "social_multi": 0.30,   # multi-source confirmed
    "social_single": 0.10   # single source
}

def calculate_dqs(signal: Signal, source_name: str, completeness: float = 1.0) -> float:
    """
    Calculates the Data Quality Score (DQS) for a signal.
    DQS = (Recency * 0.35) + (Completeness * 0.30) + (SourceReliability * 0.35)
    
    Returns a score between 0.0 and 1.0. 
    Signals with DQS < 0.40 route to the Uncertainty Engine.
    """
    # 1. Recency Score
    age_hours = (datetime.datetime.utcnow() - signal.timestamp).total_seconds() / 3600.0
    age_hours = max(0, age_hours)
    
    decay_lambda = DECAY_CONSTANTS.get(signal.category, 0.05)
    recency_score = math.exp(-decay_lambda * age_hours)
    
    # 2. Completeness Score (Provided as argument)
    completeness_score = max(0.0, min(1.0, completeness))
    
    # 3. Source Reliability
    source_score = SOURCE_RELIABILITY.get(source_name.lower(), 0.50)
    
    # Base DQS
    dqs = (recency_score * 0.35) + (completeness_score * 0.30) + (source_score * 0.35)
    
    # Contradiction penalty
    if signal.is_contradictory:
        dqs *= 0.50
        
    return dqs
