import sqlite3
import pandas as pd
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apex_data.db")
conn = sqlite3.connect(db_path)

# Query the database
df = pd.read_sql_query("SELECT * FROM daily_audit_log", conn)

if df.empty:
    print("Logbook is currently empty.")
else:
    print(f"Total Logbook Entries: {len(df)}")
    print(f"Evaluated Entries: {len(df[df['status'] == 'EVALUATED'])}")
    
    evaluated = df[df['status'] == 'EVALUATED']
    if not evaluated.empty:
        buys = evaluated[evaluated['recommendation'] == 'BUY']
        correct_buys = buys[buys['was_correct'] == 1]
        
        print("\n=== SYSTEM LOGBOOK SUMMARY (PAST 2 MONTHS) ===")
        print(f"Total BUY Recommendations: {len(buys)}")
        if len(buys) > 0:
            print(f"Successful BUYs (Profitable next day): {len(correct_buys)} ({(len(correct_buys)/len(buys))*100:.1f}%)")
            
        print("\nRecent 5 Logbook Entries:")
        print(df.tail(5)[['scan_date', 'ticker', 'recommendation', 'start_price', 'next_day_price', 'outcome_pnl_pct', 'was_correct']].to_string(index=False))

conn.close()
