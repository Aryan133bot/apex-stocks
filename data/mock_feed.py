import datetime
import random
from typing import List

from core.types import Signal, SignalCategory, SignalSubSource, DataPacket
from data.dqs import calculate_dqs

def generate_mock_signal(
    name: str, 
    category: SignalCategory, 
    sub_source: SignalSubSource, 
    age_hours: float,
    source_name: str,
    value: float = None,
    is_contradictory: bool = False
) -> Signal:
    """Helper to generate a single synthetic signal with a specific age."""
    timestamp = datetime.datetime.utcnow() - datetime.timedelta(hours=age_hours)
    
    # Assign a random value if none provided (0-100 range)
    if value is None:
        value = random.uniform(0.0, 100.0)
        
    signal = Signal(
        name=name,
        category=category,
        sub_source=sub_source,
        value=value,
        timestamp=timestamp,
        is_contradictory=is_contradictory,
        raw_data={"mock_metadata": "test"}
    )
    
    # Calculate and assign DQS immediately upon creation
    signal.dqs_score = calculate_dqs(signal, source_name=source_name)
    return signal

def generate_mock_data_packet(ticker: str) -> DataPacket:
    """Generates a realistic-looking DataPacket with mixed signal quality."""
    packet = DataPacket(ticker=ticker, timestamp=datetime.datetime.utcnow())
    
    # 1. Fresh Price Signal (Polygon, 5 mins old)
    packet.signals.append(
        generate_mock_signal(
            name="RSI_14", 
            category=SignalCategory.PRICE, 
            sub_source=SignalSubSource.PRICE_ACTION,
            age_hours=0.08, # 5 mins
            source_name="polygon",
            value=65.0
        )
    )
    
    # 2. Stale 13F Signal (FMP, 30 days old)
    # Even though it's 30 days old, 13F decays very slowly (60-day half-life)
    packet.signals.append(
        generate_mock_signal(
            name="13F_Net_Accumulation", 
            category=SignalCategory.INSTITUTIONAL, 
            sub_source=SignalSubSource.THIRTEEN_F,
            age_hours=720.0, # 30 days
            source_name="fmp",
            value=80.0
        )
    )
    
    # 3. Contradictory Sentiment Signal (Social Media, fresh)
    # Fresh, but low reliability source + contradictory flag
    packet.signals.append(
        generate_mock_signal(
            name="Retail_Sentiment", 
            category=SignalCategory.SENTIMENT, 
            sub_source=SignalSubSource.SOCIAL_MEDIA,
            age_hours=1.0,
            source_name="social_single",
            value=90.0,
            is_contradictory=True # Simulating a manipulated spike
        )
    )
    
    # 4. Fundamental Signal (FMP, 5 days old)
    packet.signals.append(
        generate_mock_signal(
            name="EPS_Acceleration", 
            category=SignalCategory.FUNDAMENTAL, 
            sub_source=SignalSubSource.FINANCIAL_STATEMENT,
            age_hours=120.0, # 5 days
            source_name="fmp",
            value=100.0
        )
    )
    
    return packet

if __name__ == "__main__":
    # Test the mock feed
    packet = generate_mock_data_packet("AAPL")
    print(f"Generated DataPacket for {packet.ticker} at {packet.timestamp}")
    print("-" * 65)
    for sig in packet.signals:
        route = "BULL/BEAR" if sig.dqs_score >= 0.40 else "UNCERTAINTY ONLY"
        print(f"Signal: {sig.name:<22} | Category: {sig.category.value:<13} | Age: {(datetime.datetime.utcnow() - sig.timestamp).total_seconds()/3600:>5.1f}h")
        print(f"  Value: {sig.value:>5.1f} | DQS: {sig.dqs_score:.3f} -> Route to: {route}")
        if sig.is_contradictory:
            print(f"  [!] Flagged as contradictory (DQS halved)")
        print("-" * 65)
