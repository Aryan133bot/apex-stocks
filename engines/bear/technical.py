import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class TechnicalBearEngine(BaseEngine):
    """
    Evaluates extreme technical breakdown (crashing through 200DMA on high volume).
    High score = High Tail Risk (Veto/Sell).
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BEAR)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # Distance from 200 DMA (%)
        dist_200d = next((s.value for s in signals if s.name == "DIST_200DMA"), 0.0)
        # Down-volume expansion (measured in multiples of 30D average volume)
        vol_expansion = next((s.value for s in signals if s.name == "DOWN_VOL_EXPANSION"), 0.0)
        
        score = 0.0
        
        # Severe structural breakdown
        if dist_200d < -0.05: score += 50.0 # Broken below 200DMA by 5%
        if dist_200d < -0.15: score += 30.0 # Broken below 200DMA by 15% (Death spiral)
        
        # Volume expansion on down days adds tail risk
        score += min(20.0, vol_expansion * 5.0)
        
        return {
            "score": min(100.0, score)
        }
