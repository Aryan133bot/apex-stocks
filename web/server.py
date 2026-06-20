import os
import json
import uvicorn
import yfinance as yf
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.store import get_portfolio, add_portfolio_position, remove_portfolio_position, initialize_database

app = FastAPI()

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class PortfolioItem(BaseModel):
    ticker: str
    buy_price: float
    quantity: int
    term_category: str

@app.on_event("startup")
def startup():
    initialize_database()
    print("[APEX] Starting interactive Web UI on http://127.0.0.1:8000")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/api/recommendations")
def get_recommendations():
    """Reads the Top 100 stock data directly from the nightly scanner JSON file."""
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "latest_scan.json")
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            return json.load(f)
    else:
        return {"regime_state": 0, "regime_mult": 0.0, "stocks": []}

@app.get("/api/smallcap")
def get_smallcap_recommendations():
    """Reads the smallcap stock data directly from the smallcap_scan.json file."""
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "smallcap_scan.json")
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            return json.load(f)
    else:
        return {"candidates": []}

@app.get("/api/portfolio")
def fetch_portfolio():
    return get_portfolio()

@app.get("/api/portfolio/enriched")
def fetch_enriched_portfolio():
    """Returns portfolio positions with live prices and PnL calculations."""
    positions = get_portfolio()
    if not positions:
        return {"positions": [], "total_invested": 0, "total_current": 0, "total_pnl": 0, "total_pnl_pct": 0}
    
    tickers = [p['ticker'] for p in positions]
    live_prices = {}
    
    def fetch_price(t):
        try:
            return t, yf.Ticker(t + ".NS").fast_info.last_price
        except:
            return t, None
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_price, tickers)
        for t, p in results:
            if p is not None:
                live_prices[t] = p
    
    total_invested = 0
    total_current = 0
    enriched = []
    
    for p in positions:
        invested = p['buy_price'] * p['quantity']
        current_price = live_prices.get(p['ticker'], p['buy_price'])
        current_value = current_price * p['quantity']
        pnl = current_value - invested
        pnl_pct = ((current_price / p['buy_price']) - 1) * 100 if p['buy_price'] > 0 else 0
        
        total_invested += invested
        total_current += current_value
        
        enriched.append({
            **p,
            "current_price": round(current_price, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2)
        })
    
    total_pnl = total_current - total_invested
    total_pnl_pct = ((total_current / total_invested) - 1) * 100 if total_invested > 0 else 0
    
    return {
        "positions": enriched,
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2)
    }

class LivePriceRequest(BaseModel):
    tickers: list[str]

@app.post("/api/live_prices")
def get_live_prices(req: LivePriceRequest):
    tickers = req.tickers
    prices = {}
    
    def fetch_price(t):
        try:
            return t, yf.Ticker(t + ".NS").fast_info.last_price
        except:
            return t, None
            
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_price, tickers)
        for t, p in results:
            if p is not None:
                prices[t] = p
                
    return prices

@app.post("/api/portfolio")
def add_to_portfolio(item: PortfolioItem):
    date_added = datetime.now().strftime("%Y-%m-%d")
    add_portfolio_position(item.ticker, item.buy_price, item.quantity, item.term_category, date_added)
    return {"status": "success"}

@app.delete("/api/portfolio/{position_id}")
def delete_from_portfolio(position_id: int):
    remove_portfolio_position(position_id)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
