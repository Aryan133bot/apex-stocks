import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class OptionsFlowEngine(BaseEngine):
    """
    Evaluates NSE F&O Options Flow.
    Focuses on Open Interest (OI) buildup, Put-Call Ratio (PCR), and Implied Volatility (IV) Rank.
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BULL)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # O1: Put-Call Ratio (Contrarian / Sentiment indicator)
        pcr = next((s.value for s in signals if s.name == "PCR"), 1.0)
        pcr_score = 50.0
        if pcr < 0.6: pcr_score = 90.0 # Heavy put selling / oversold -> Bullish
        elif pcr > 1.4: pcr_score = 10.0 # Call heavy / overbought -> Bearish
        
        # O2: IV Rank (0-100 scale)
        ivr = next((s.value for s in signals if s.name == "IV_RANK"), 50.0)
        ivr_score = max(0.0, 100.0 - ivr) # Lower IV rank is generally better for directional bulls
        
        # O3: OI Change (Net Put OI Addition)
        # Positive values mean Put writers are aggressively building support
        oi_chg = next((s.value for s in signals if s.name == "NET_PUT_OI_ADDITION"), 0.0)
        oi_score = max(0.0, min(100.0, 50.0 + (oi_chg * 10.0)))
        
        # Weigh OI heavily as it represents institutional support levels
        final_score = (pcr_score * 0.3) + (oi_score * 0.5) + (ivr_score * 0.2)
        
        return {
            "score": final_score, 
            "pcr_score": pcr_score, 
            "oi_score": oi_score,
            "ivr_score": ivr_score
        }
