# APEX Quantitative Trading System

A full-stack, institutional-grade algorithmic trading architecture built in Python. This system is designed to autonomously execute capital-efficient compounding strategies with a strong focus on risk management and regime detection.

## 🚀 Key Features

*   **Market Regime Detection**: Utilizes a Hidden Markov Model (HMM) to constantly classify the broader market into Bull, Bear, or Sideways states, automatically scaling position sizes to protect capital.
*   **Alpha Momentum Scanner**: A high-velocity small-cap equity scanner that utilizes vectorized NumPy backtesting. It actively screens for high-probability decadal setups, filtering by volume anomalies, fundamental strength, and promoter pledging.
*   **Vectorized Backtesting Engine**: Capable of processing years of historical market data and simulating the performance of strategies in milliseconds to validate mathematical edge.
*   **Live Interactive Dashboard**: A custom-built FastAPI web backend and vanilla Javascript/CSS frontend that provides real-time portfolio tracking, algorithmic buy/sell/hold signals, and live PnL updates.
*   **Strict Risk Management**: Integrated liquidity gates, dynamic position sizing based on portfolio value, and hard trailing stop-losses.

## 🛠️ Technology Stack

*   **Core**: Python, Pandas, NumPy, Scikit-learn (HMM models)
*   **Data Integration**: `yfinance`, NSE Option Chain feeds, Fundamental screeners
*   **Web Framework**: FastAPI, Uvicorn
*   **Frontend UI**: HTML5, Vanilla CSS (Custom dark-mode UI), Javascript
*   **Version Control**: Git

## 🧠 Architecture Overview

1.  **Data Fetchers**: Modular adapters that stream raw OHLCV pricing, institutional holdings, and macro-economic metrics.
2.  **Engines**: 
    *   `regime/`: Machine Learning models (HMM) to define market context.
    *   `smallcap/`: The High-Velocity momentum compounding engine for aggressive growth.
    *   `bull/` & `bear/`: Targeted fundamental and technical screeners.
3.  **Web Module**: Exposes JSON APIs and hosts the live portfolio tracking UI.

## 📈 The Philosophy: High-Velocity Compounding

This specific system is currently tuned for the "Small Account Challenge" (e.g., compounding a ₹10,000 account). It completely avoids the trap of over-diversification. Instead, it identifies the single highest-probability momentum setup daily and allocates capital aggressively with tight (-6%) trailing stops, mimicking the wealth-creation strategies of prop desk traders.

---
*Disclaimer: This system was built for educational and portfolio demonstration purposes. Algorithmic trading involves significant risk.*
