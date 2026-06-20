import schedule
import time
import subprocess
import os

def trigger_scan():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Triggering daily APEX scan...")
    script_path = os.path.join(os.path.dirname(__file__), 'run_daily_scan.py')
    
    # Run the massive 500-stock scanner
    subprocess.run(["python", script_path])
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Scan complete. The Web UI has been automatically updated with new data.")

# Indian markets close at 15:30 IST. 
# We schedule the quantitative scan for 16:30 IST to ensure all closing data is finalized by the exchanges.
schedule.every().day.at("16:30").do(trigger_scan)

if __name__ == "__main__":
    print("=== APEX AUTONOMOUS SCHEDULER ===")
    print("Scheduler is now running in the background.")
    print("It will automatically download new market data and update the UI every day at 16:30 IST.")
    
    while True:
        schedule.run_pending()
        time.sleep(60) # Check every minute
