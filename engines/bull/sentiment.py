import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class SentimentBullEngine(BaseEngine):
    """
    Evaluates NLP FinBERT sentiment from local Indian news sources (Moneycontrol, ET).
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BULL)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # FinBERT Score (-1.0 to 1.0)
        finbert = next((s.value for s in signals if s.name == "FINBERT_SENTIMENT"), 0.0)
        
        # Map -1.0 -> 0 score, 0.0 -> 50 score, 1.0 -> 100 score
        final_score = max(0.0, min(100.0, (finbert + 1.0) * 50.0))
        
        return {
            "score": final_score
        }
