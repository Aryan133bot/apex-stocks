import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class MomentumBullEngine(BaseEngine):
    """
    Evaluates pure price momentum and moving average structures.
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BULL)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # Distance from 200 DMA (%)
        dist_200d = next((s.value for s in signals if s.name == "DIST_200DMA"), 0.0)
        # Distance from 50 DMA (%)
        dist_50d = next((s.value for s in signals if s.name == "DIST_50DMA"), 0.0)
        
        # If price is 10% above 200DMA -> score is 70
        score_200 = max(0.0, min(100.0, 50.0 + (dist_200d * 200.0)))
        score_50 = max(0.0, min(100.0, 50.0 + (dist_50d * 200.0)))
        
        final_score = (score_200 * 0.4) + (score_50 * 0.6)
        
        return {
            "score": final_score,
            "score_200dma": score_200,
            "score_50dma": score_50
        }
