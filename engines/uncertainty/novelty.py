import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class NoveltyEngine(BaseEngine):
    """
    Detects market conditions that the HMM has not seen before (Black Swan detection).
    High novelty = Extreme Uncertainty.
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.UNCERTAINTY)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # 1.0 = Yes, VIX spiked by >40% in a single session
        vix_spike = next((s.value for s in signals if s.name == "VIX_EXTREME_SPIKE"), 0.0)
        
        # 0 to 100 anomaly score (distance from normal distribution bounds)
        anomaly_score = next((s.value for s in signals if s.name == "MARKET_ANOMALY_SCORE"), 0.0)
        
        score = anomaly_score
        if vix_spike == 1.0: score += 60.0
        
        return {
            "score": min(100.0, score)
        }
