import numpy as np
from typing import Dict, Any
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

class RelativeStrengthEngine(BaseEngine):
    """
    Evaluates price momentum relative to benchmarks (Nifty 50 and NSE Sectors).
    """
    def __init__(self):
        super().__init__(engine_type=EngineType.BULL)
        
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        """
        Expects 3 specific signals in the data packet:
        - STOCK_63D_RET
        - NIFTY_63D_RET
        - SECTOR_63D_RET
        """
        stock_63d = next((s.value for s in data_packet.signals if s.name == "STOCK_63D_RET"), 0.0)
        nifty_63d = next((s.value for s in data_packet.signals if s.name == "NIFTY_63D_RET"), 0.0)
        sector_63d = next((s.value for s in data_packet.signals if s.name == "SECTOR_63D_RET"), 0.0)
        
        # RS1: Stock vs Market (Nifty 50)
        rs1_diff = stock_63d - nifty_63d
        # RS2: Stock vs Sector
        rs2_diff = stock_63d - sector_63d
        # RS3: Sector vs Market
        rs3_diff = sector_63d - nifty_63d
        
        # Map outperformance to a 0-100 score
        # A 15% outperformance (+0.15) yields ~80 score. 
        def map_rs(val):
            score = 50 + (val * 200)
            return float(max(0.0, min(100.0, score)))
            
        rs1_score = map_rs(rs1_diff)
        rs2_score = map_rs(rs2_diff)
        rs3_score = map_rs(rs3_diff)
        
        # Base weightings: 40% vs Market, 40% vs Sector, 20% Sector vs Market tailwind
        final_score = (rs1_score * 0.40) + (rs2_score * 0.40) + (rs3_score * 0.20)
        
        return {
            "score": final_score,
            "rs1_nifty_score": rs1_score,
            "rs2_sector_score": rs2_score,
            "rs3_sector_nifty_score": rs3_score,
            "raw_diffs": {
                "stock_vs_nifty": rs1_diff,
                "stock_vs_sector": rs2_diff,
                "sector_vs_nifty": rs3_diff
            }
        }
