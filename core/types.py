from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import datetime

class SignalCategory(Enum):
    PRICE = "price"
    VOLUME = "volume"
    FUNDAMENTAL = "fundamental"
    INSTITUTIONAL = "institutional"
    MACRO = "macro"
    SENTIMENT = "sentiment"
    OPTIONS = "options"

class SignalSubSource(Enum):
    DARK_POOL = "dark_pool"
    THIRTEEN_F = "13f"
    INSIDER = "insider"
    PRICE_ACTION = "price_action"
    OPTIONS_FLOW = "options_flow"
    FINANCIAL_STATEMENT = "financial_statement"
    ANALYST_REVISION = "analyst_revision"
    NEWS_ARTICLE = "news_article"
    SOCIAL_MEDIA = "social_media"
    CREDIT_MARKET = "credit_market"

class EngineType(Enum):
    BULL = "bull"
    BEAR = "bear"
    UNCERTAINTY = "uncertainty"
    REGIME = "regime"

@dataclass
class Signal:
    """Represents an atomic piece of evidence used by the engines. 
    Includes Independence Tagging to prevent circular reasoning in the Debate Engine."""
    name: str
    category: SignalCategory
    sub_source: SignalSubSource
    value: float  # The raw or normalized score of this signal (0-100 generally)
    timestamp: datetime.datetime
    dqs_score: float = 1.0  # Data Quality Score
    is_contradictory: bool = False
    raw_data: Any = None # The underlying data point
    metadata: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class DataPacket:
    """Encapsulates a collection of signals for a specific ticker at a specific time."""
    ticker: str
    timestamp: datetime.datetime
    signals: List[Signal] = field(default_factory=list)
    
    def get_signals_by_category(self, category: SignalCategory) -> List[Signal]:
        return [s for s in self.signals if s.category == category]
