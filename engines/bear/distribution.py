import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class DistributionBearEngine(BaseEngine):
    """
    Evaluates institutional distribution (FII offloading, bulk deal sellers).
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BEAR)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        fii_sig = next((s for s in signals if s.name == "FII_10D_ZSCORE"), None)
        fii_score = 0.0
        if fii_sig and fii_sig.value < -1.5: fii_score = 80.0
        elif fii_sig and fii_sig.value < -0.5: fii_score = 40.0
        
        bulk_sig = next((s for s in signals if s.name == "BULK_DEAL_SELLERS"), None)
        bulk_score = bulk_sig.value if bulk_sig else 0.0
        
        final_score = min(100.0, (fii_score * 0.6) + (bulk_score * 0.4))
        
        return {
            "score": final_score
        }
