import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class PromoterBearEngine(BaseEngine):
    """
    Evaluates extreme structural risk based on Promoter behavior.
    High score = High Bearishness (Sell/Reject signal).
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BEAR)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # Absolute pledge percentage
        pledge_pct = next((s.value for s in signals if s.name == "PROMOTER_PLEDGE_PCT"), 0.0)
        # Quarter over quarter pledge change
        pledge_chg = next((s.value for s in signals if s.name == "PROMOTER_PLEDGE_CHG"), 0.0)
        # Quarter over quarter holding change
        holding_chg = next((s.value for s in signals if s.name == "PROMOTER_HOLDING_CHG"), 0.0)
        
        score = 0.0
        
        # Heavy pledging is a massive red flag in India (risk of margin calls on promoters)
        if pledge_pct > 25.0: score += 50.0
        if pledge_chg > 2.0: score += 30.0
        
        # Direct promoter selling
        if holding_chg < -1.0: score += 50.0
        elif holding_chg < -0.5: score += 20.0
        
        final_score = min(100.0, score)
        
        return {
            "score": final_score, 
            "pledge_pct": pledge_pct,
            "holding_chg": holding_chg
        }
