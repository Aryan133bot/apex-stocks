import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class FundamentalBullEngine(BaseEngine):
    """
    Evaluates Indian GAAP fundamental strength.
    Focuses on clean PAT growth (stripping exceptional items), EBITDA margins, and ROE.
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BULL)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # Clean Profit After Tax (YoY Growth %)
        pat_growth = next((s.value for s in signals if s.name == "PAT_GROWTH_YOY"), 0.0)
        # EBITDA Margin (%)
        ebitda_margin = next((s.value for s in signals if s.name == "EBITDA_MARGIN"), 0.0)
        # Return on Equity (%)
        roe = next((s.value for s in signals if s.name == "ROE"), 0.0)
        
        # Score mapping functions
        # 20% PAT growth -> 70 score
        pat_score = max(0.0, min(100.0, 50.0 + (pat_growth * 100.0)))
        
        # 15% margin -> 45 score, 30% margin -> 90 score
        ebitda_score = max(0.0, min(100.0, ebitda_margin * 3.0))
        
        # 15% ROE -> 60 score
        roe_score = max(0.0, min(100.0, roe * 4.0))
        
        # PAT growth is the primary driver of bull runs in Indian markets
        final_score = (pat_score * 0.50) + (ebitda_score * 0.25) + (roe_score * 0.25)
        
        return {
            "score": final_score, 
            "pat_score": pat_score,
            "ebitda_score": ebitda_score,
            "roe_score": roe_score
        }
