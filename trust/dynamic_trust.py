class DynamicTrust:
    """
    Adjusts the final score weightings of any Engine based on the raw Data Quality Scores (DQS).
    """
    def __init__(self):
        pass
        
    def apply_trust_discount(self, engine_score: float, average_dqs: float) -> float:
        """
        If the data quality is 1.0 (100%), trust is 1.0 (no discount).
        If DQS is 0.5 (50%), the engine score is heavily discounted.
        
        Uses a non-linear (squared) discount to heavily penalize missing/corrupt data.
        """
        # Ensure DQS is bounded
        avg_dqs = max(0.0, min(1.0, average_dqs))
        
        trust_factor = avg_dqs ** 2
        return float(engine_score * trust_factor)
