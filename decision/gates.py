class LiquidityGate:
    """
    Indian Market Liquidity Gate.
    Ensures position sizing never exceeds 5% of the 20-Day Average Daily Volume (ADV).
    Replaces the US algorithmic Kyle's Lambda execution logic.
    """
    def __init__(self, max_adv_pct=0.05):
        self.max_adv_pct = max_adv_pct
        
    def check_liquidity(self, target_capital: float, current_price: float, adv_20d: int) -> dict:
        """
        Evaluates if the target capital deployment is safe given the stock's recent volume.
        Returns the maximum safe quantity to buy.
        """
        if adv_20d <= 0 or current_price <= 0:
            return {
                "approved": False,
                "approved_shares": 0,
                "reason": "Invalid ADV or price."
            }
            
        max_safe_shares = int(adv_20d * self.max_adv_pct)
        target_shares = int(target_capital / current_price)
        
        if target_shares <= max_safe_shares:
            return {
                "approved": True,
                "approved_shares": target_shares,
                "reason": f"Liquidity sufficient. Target is {(target_shares/adv_20d):.2%} of ADV."
            }
        else:
            return {
                "approved": False, # Partially approved, heavily capped
                "approved_shares": max_safe_shares,
                "reason": f"Liquidity constrained. Order capped at {self.max_adv_pct*100}% of {adv_20d} ADV."
            }
