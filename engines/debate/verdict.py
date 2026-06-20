class VerdictEngine:
    """
    The final judge. Weighs the output of the Bull, Bear, and Uncertainty engines
    against the Regime multiplier to produce a final BUY/HOLD/REJECT decision.
    """
    def __init__(self, veto_threshold=80.0, buy_threshold=38.0, hold_threshold=28.0):
        self.veto_threshold = veto_threshold
        self.buy_threshold = buy_threshold
        self.hold_threshold = hold_threshold
        
    def generate_verdict(self, bull_score: float, bear_score: float, uncertainty_score: float, regime_bull_multiplier: float) -> dict:
        """
        Debate Logic:
        1. If Bear Score > Veto Threshold, instant REJECT.
        2. Soften the Regime multiplier so it acts as a POSITION SIZER, not a kill switch.
        3. Subtract Uncertainty penalty.
        4. Output final categorization with position sizing.
        """
        # 1. Bear Veto Check
        if bear_score >= self.veto_threshold:
            return {
                "decision": "REJECT",
                "final_score": 0.0,
                "position_size_pct": 0,
                "reason": f"Bear Engine veto activated (Distress Score: {bear_score:.1f})"
            }
            
        # 2. Softened Regime Adjustment
        # Instead of raw multiplication (which zeroes everything in crisis),
        # use a floor so the effective multiplier ranges from 0.50 to 1.0
        # Formula: effective_mult = 0.50 + 0.50 * raw_mult
        # At raw 0.18 (Crisis) -> effective 0.59 (cautious but not blind)
        # At raw 0.72 (Bull)   -> effective 0.86 (near full conviction)
        effective_mult = 0.50 + (0.50 * regime_bull_multiplier)
        adjusted_bull = bull_score * effective_mult
        
        # 3. Uncertainty penalty (50% of uncertainty score is deducted)
        final_score = adjusted_bull - (uncertainty_score * 0.5)
        final_score = max(0.0, min(100.0, final_score))
        
        # 4. Position sizing based on raw regime confidence
        if regime_bull_multiplier >= 0.65:
            position_size_pct = 100  # Full conviction
        elif regime_bull_multiplier >= 0.50:
            position_size_pct = 75   # High confidence
        elif regime_bull_multiplier >= 0.35:
            position_size_pct = 50   # Moderate - half position
        else:
            position_size_pct = 25   # Crisis - quarter position only
        
        # 5. Final Verdict
        if final_score >= self.buy_threshold:
            decision = "BUY"
        elif final_score >= self.hold_threshold:
            decision = "HOLD"
        else:
            decision = "REJECT"
            
        return {
            "decision": decision,
            "final_score": final_score,
            "position_size_pct": position_size_pct,
            "reason": f"Raw Bull: {bull_score:.1f} | Effective Mult: {effective_mult:.2f} | Regime Raw: {regime_bull_multiplier:.2f}"
        }
