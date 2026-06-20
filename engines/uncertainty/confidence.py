import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class ConfidenceEngine(BaseEngine):
    """
    Evaluates Data Quality Scoring (DQS).
    If our fetchers failed (e.g., NSE blocked the FII API), confidence drops and uncertainty spikes.
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.UNCERTAINTY)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # Base confidence starts at 100%
        confidence = 100.0
        
        # Check every signal's DQS (Data Quality Score) metadata
        for sig in signals:
            if sig.dqs_score < 0.5:
                confidence -= 10.0 # Penalty for low quality/stale data
            elif sig.dqs_score == 0.0:
                confidence -= 25.0 # Massive penalty for missing/null data
                
        confidence = max(0.0, confidence)
        
        # Invert confidence into an uncertainty score (100 confidence = 0 uncertainty)
        uncertainty = 100.0 - confidence
        
        return {
            "score": min(100.0, uncertainty)
        }
