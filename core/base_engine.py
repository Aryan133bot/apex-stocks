from abc import ABC, abstractmethod
from typing import Dict, Any, List
from core.types import DataPacket, EngineType

class BaseEngine(ABC):
    """
    Abstract base class for all APEX analytical engines.
    Ensures a standardized interface for the Debate and Decision engines to interact with.
    """
    
    def __init__(self, engine_type: EngineType):
        self.engine_type = engine_type
        
    @abstractmethod
    def evaluate(self, data_packet: DataPacket) -> Dict[str, Any]:
        """
        Evaluates the incoming data packet and returns the engine's mathematical outputs.
        
        Args:
            data_packet: A DataPacket containing all signals tagged with their DQS 
                         and independence source tags.
            
        Returns:
            Dict containing the final mathematical score, sub-module scores, 
            and relevant metadata (e.g., confidence intervals for the Uncertainty Engine).
        """
        pass
