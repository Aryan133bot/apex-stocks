import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class DistressBearEngine(BaseEngine):
    """
    The ultimate veto engine.
    Looks for IBC/NCLT insolvency cases, Auditor Qualifications, and toxic NPAs.
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BEAR)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        signals = data_packet.signals
        
        # 1.0 = True, 0.0 = False
        is_nclt = next((s.value for s in signals if s.name == "IBC_NCLT_STATUS"), 0.0)
        auditor_qual = next((s.value for s in signals if s.name == "AUDITOR_QUALIFICATION"), 0.0)
        # Gross Non-Performing Assets (for banks/NBFCs)
        npa_pct = next((s.value for s in signals if s.name == "GROSS_NPA_PCT"), 0.0)
        
        score = 0.0
        
        # Insolvency is an instant 100/100 Bear Score (Instant Veto)
        if is_nclt == 1.0: score += 100.0
        
        # Auditor raising red flags on financial statements
        if auditor_qual == 1.0: score += 80.0
        
        # High NPAs kill financial stocks
        if npa_pct > 5.0: score += (npa_pct * 10.0)
        
        final_score = min(100.0, score)
        return {
            "score": final_score
        }
