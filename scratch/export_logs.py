import sqlite3
import pandas as pd
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apex_data.db")
output_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "historical_logbook.csv")

try:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM daily_audit_log ORDER BY scan_date DESC, id DESC", conn)
    df.to_csv(output_csv, index=False)
    conn.close()
    print(f"Successfully exported {len(df)} logs to {output_csv}")
except Exception as e:
    print(f"Error exporting logs: {e}")
