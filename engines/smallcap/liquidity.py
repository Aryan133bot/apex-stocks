class SmallCapLiquidity:
    def __init__(self, portfolio_capital):
        self.portfolio_capital = portfolio_capital

    def calculate_exit_safety(self, stop_loss_pct, avg_turnover_20d, pattern_type):
        """
        Step 1: Calculate intended position size based on risk and module rules.
        Step 2: Calculate Exit Liquidity Ratio.
        Step 3: Return final safe position size, ratio, and safety status.
        """
        # Maximum capital in small-cap module is 30% of portfolio.
        # Max single position is 8% of total portfolio.
        max_position_value = self.portfolio_capital * 0.08
        
        # Risk based sizing:
        # P1 = -12% stop, P2 = -8% stop, P3 = -10% stop
        if pattern_type == "PATTERN 1":
            stop_loss = 0.12
        elif pattern_type == "PATTERN 2":
            stop_loss = 0.08
        elif pattern_type == "PATTERN 3":
            stop_loss = 0.10
        else:
            stop_loss = 0.10
            
        if stop_loss_pct > 0:
            stop_loss = stop_loss_pct
            
        # We risk 2% of the TOTAL portfolio on this trade
        risk_amount = self.portfolio_capital * 0.02
        intended_position = min(risk_amount / stop_loss, max_position_value)
        
        # Liquidity Ratio calculation
        # You shouldn't be more than 10% of a day's average volume
        safe_daily_exit = avg_turnover_20d * 0.10
        
        exit_liquidity_ratio = intended_position / safe_daily_exit if safe_daily_exit > 0 else 999.0
        
        if exit_liquidity_ratio <= 1.0:
            status = "SAFE"
            final_position = intended_position
        elif exit_liquidity_ratio <= 2.0:
            status = "CAUTION"
            final_position = intended_position * 0.5 # Reduce size by half
        else:
            status = "REJECT"
            final_position = 0.0
            
        return {
            "intended_position": round(intended_position, 2),
            "final_position": round(final_position, 2),
            "exit_liquidity_ratio": round(exit_liquidity_ratio, 2),
            "status": status,
            "max_holding_days": 10 if avg_turnover_20d <= 50_000_000 else None
        }
