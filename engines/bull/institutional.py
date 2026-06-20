import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class InstitutionalBullEngine(BaseEngine):
    """
    Evaluates institutional (FII/DII) flows, Bulk Deals, and Promoter Buying.
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BULL)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # F1: FII Net Flow (Rolling 10D z-score)
        fii_score = 50.0
        fii_sig = next((s for s in signals if s.name == "FII_10D_ZSCORE"), None)
        if fii_sig:
            z = fii_sig.value
            if z > 2.0: fii_score = 90.0
            elif z > 1.0: fii_score = 70.0
            elif z < -2.0: fii_score = 10.0
            elif z < -1.0: fii_score = 30.0
            
        # F2: Bulk/Block Deals (0 to 100 confidence score based on buyer quality)
        bulk_score = 50.0
        bulk_sig = next((s for s in signals if s.name == "BULK_DEAL_SCORE"), None)
        if bulk_sig:
            bulk_score = max(0.0, min(100.0, bulk_sig.value))
            
        # F3: Promoter Buying (% change quarter over quarter)
        promoter_score = 50.0
        promoter_sig = next((s for s in signals if s.name == "PROMOTER_HOLDING_CHG"), None)
        if promoter_sig:
            chg = promoter_sig.value
            if chg > 1.0: promoter_score = 80.0
            elif chg > 0.0: promoter_score = 65.0
            elif chg < -1.0: promoter_score = 20.0
            elif chg < 0.0: promoter_score = 35.0
            
        final_score = (fii_score * 0.45) + (bulk_score * 0.30) + (promoter_score * 0.25)
        
        return {
            "score": final_score,
            "fii_flow_score": fii_score,
            "bulk_deal_score": bulk_score,
            "promoter_score": promoter_score
        }
