import sqlite3
import pandas as pd
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apex_data.db")
conn = sqlite3.connect(db_path)
df = pd.read_sql_query("SELECT * FROM daily_audit_log WHERE status = 'EVALUATED' AND recommendation = 'BUY'", conn)
conn.close()

if df.empty:
    print("No evaluated BUY data found.")
    exit()

df['scan_date'] = pd.to_datetime(df['scan_date'])
df = df.sort_values('scan_date')

starting_capital = 10000.0
capital = starting_capital
risk_per_trade_pct = 0.02

grouped = df.groupby('scan_date')
daily_history = []

for date, group in grouped:
    daily_profit = 0.0
    total_capital_deployed = 0.0
    
    # We sort by highest momentum or something to pick the best ones if we have too many
    # Here we just iterate in whatever order they come
    for _, row in group.iterrows():
        start_price = row['start_price']
        stop_loss = row['stop_loss']
        outcome_pnl_pct = row['outcome_pnl_pct']
        
        # Calculate capital allocated to this trade using the 2% risk rule
        risk_amount = capital * risk_per_trade_pct
        risk_per_share = start_price - stop_loss
        
        if risk_per_share <= 0:
            position_size = capital * 0.05 # Fallback to 5% flat weight if SL is broken
        else:
            position_size = (risk_amount / risk_per_share) * start_price
            
        # Cap the position size so we don't put more than 25% of our portfolio in one stock
        max_position = capital * 0.25
        if position_size > max_position:
            position_size = max_position
            
        if total_capital_deployed + position_size <= capital:
            trade_profit = position_size * (outcome_pnl_pct / 100.0)
            
            # Simulated stop-loss hit checking
            max_loss_pct = ((stop_loss - start_price) / start_price) * 100
            if outcome_pnl_pct < max_loss_pct:
                trade_profit = position_size * (max_loss_pct / 100.0) # Stop out at max loss
                
            daily_profit += trade_profit
            total_capital_deployed += position_size
            
    capital += daily_profit
    
    daily_pnl_pct = (daily_profit / capital) * 100 if capital > 0 else 0
    
    daily_history.append({
        'date': date.strftime('%Y-%m-%d'),
        'capital': capital,
        'daily_pnl_pct': daily_pnl_pct,
        'profit_rs': daily_profit,
        'stocks_traded': len(group)
    })

res_df = pd.DataFrame(daily_history)

print("=== APEX 60-DAY BACKTEST SIMULATION ===")
print("Model: 2.0% Risk Parity & ATR Trailing Stop")
print(f"Starting Capital: Rs.{starting_capital:,.2f}")
print(f"Final Capital: Rs.{capital:,.2f}")
print("-" * 40)
total_profit = capital - starting_capital
total_return = (total_profit / starting_capital) * 100
print(f"Total Profit: Rs.{total_profit:,.2f}")
print(f"Total Return: {total_return:.2f}% in ~2 Months")

win_days = len(res_df[res_df['daily_pnl_pct'] > 0])
loss_days = len(res_df[res_df['daily_pnl_pct'] <= 0])
win_rate_days = (win_days / len(res_df)) * 100

print(f"Trading Days Won: {win_days}")
print(f"Trading Days Lost: {loss_days}")
print(f"Daily Win Rate: {win_rate_days:.1f}%")
