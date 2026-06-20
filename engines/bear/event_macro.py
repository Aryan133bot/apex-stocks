import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class MacroBearEngine(BaseEngine):
    """
    Evaluates Indian macroeconomic headwinds (RBI MPC, Union Budget uncertainty, INR drops).
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BEAR)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # Event risk (0-100) mapped from proximity to Budget/Elections/MPC
        event_risk = next((s.value for s in signals if s.name == "MACRO_EVENT_RISK"), 0.0)
        # USD/INR Depreciation severity
        inr_depreciation = next((s.value for s in signals if s.name == "USDINR_DEPRECIATION"), 0.0)
        
        score = (event_risk * 0.5) + (inr_depreciation * 0.5)
        
        return {
            "score": min(100.0, score)
        }
