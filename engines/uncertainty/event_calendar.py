import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class EventCalendarEngine(BaseEngine):
    """
    Evaluates known forward-looking Indian market events that generate volatility.
    High score = High Uncertainty (Reduces position sizes or pauses trading).
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.UNCERTAINTY)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # Binary flags (1.0 = Active event this week, 0.0 = No event)
        is_expiry_week = next((s.value for s in signals if s.name == "FNO_EXPIRY_WEEK"), 0.0)
        is_mpc_week = next((s.value for s in signals if s.name == "RBI_MPC_WEEK"), 0.0)
        # 0.0 to 1.0 proximity score
        is_budget_month = next((s.value for s in signals if s.name == "UNION_BUDGET_PROXIMITY"), 0.0)
        
        score = 0.0
        
        # Monthly Expiry (last Thursday) generates massive localized F&O volatility
        if is_expiry_week == 1.0: score += 30.0
        
        # RBI MPC brings strict rate uncertainty
        if is_mpc_week == 1.0: score += 40.0
        
        # Union budget (Feb 1) brings massive systemic uncertainty (taxes, capex)
        if is_budget_month > 0.0: score += (is_budget_month * 50.0)
        
        return {
            "score": min(100.0, score)
        }
