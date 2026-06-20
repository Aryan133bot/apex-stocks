# NSE Sector Index Mapping
# Maps each stock ticker to its corresponding Nifty sectoral index for accurate RS calculations

SECTOR_MAP = {
    # Banking & Financial Services -> Nifty Bank
    "HDFCBANK.NS": "^NSEBANK", "ICICIBANK.NS": "^NSEBANK", "SBIN.NS": "^NSEBANK",
    "AXISBANK.NS": "^NSEBANK", "KOTAKBANK.NS": "^NSEBANK", "INDUSINDBK.NS": "^NSEBANK",
    "PNB.NS": "^NSEBANK", "BANKBARODA.NS": "^NSEBANK",
    "BAJFINANCE.NS": "^NSEBANK", "BAJAJFINSV.NS": "^NSEBANK", "CHOLAFIN.NS": "^NSEBANK",
    "MUTHOOTFIN.NS": "^NSEBANK", "BAJAJHLDNG.NS": "^NSEBANK",
    "SBILIFE.NS": "^NSEBANK", "HDFCLIFE.NS": "^NSEBANK", "ICICIGI.NS": "^NSEBANK",
    "ICICIPRULI.NS": "^NSEBANK", "HDFCAMC.NS": "^NSEBANK",
    
    # IT -> Nifty IT
    "TCS.NS": "^CNXIT", "INFY.NS": "^CNXIT", "HCLTECH.NS": "^CNXIT",
    "WIPRO.NS": "^CNXIT", "TECHM.NS": "^CNXIT", "LTTS.NS": "^CNXIT",
    "PERSISTENT.NS": "^CNXIT", "MPHASIS.NS": "^CNXIT", "OFSS.NS": "^CNXIT",
    "TATAELXSI.NS": "^CNXIT",
    
    # Pharma -> Nifty Pharma
    "SUNPHARMA.NS": "^CNXPHARMA", "DRREDDY.NS": "^CNXPHARMA", "CIPLA.NS": "^CNXPHARMA",
    "DIVISLAB.NS": "^CNXPHARMA", "APOLLOHOSP.NS": "^CNXPHARMA", "TORNTPHARM.NS": "^CNXPHARMA",
    "AUROPHARMA.NS": "^CNXPHARMA", "LUPIN.NS": "^CNXPHARMA", "ZYDUSLIFE.NS": "^CNXPHARMA",
    "ALKEM.NS": "^CNXPHARMA", "BIOCON.NS": "^CNXPHARMA",
    
    # Auto -> Nifty Auto
    "MARUTI.NS": "^CNXAUTO", "BAJAJ-AUTO.NS": "^CNXAUTO", "TVSMOTOR.NS": "^CNXAUTO",
    "EICHERMOT.NS": "^CNXAUTO", "HEROMOTOCO.NS": "^CNXAUTO", "M&M.NS": "^CNXAUTO",
    
    # Metals & Mining -> Nifty Metal
    "TATASTEEL.NS": "^CNXMETAL", "JSWSTEEL.NS": "^CNXMETAL", "HINDALCO.NS": "^CNXMETAL",
    "JINDALSTEL.NS": "^CNXMETAL", "COALINDIA.NS": "^CNXMETAL",
    
    # FMCG -> Nifty FMCG
    "HINDUNILVR.NS": "^CNXFMCG", "ITC.NS": "^CNXFMCG", "NESTLEIND.NS": "^CNXFMCG",
    "BRITANNIA.NS": "^CNXFMCG", "TATACONSUM.NS": "^CNXFMCG", "GODREJCP.NS": "^CNXFMCG",
    "DABUR.NS": "^CNXFMCG", "COLPAL.NS": "^CNXFMCG", "MARICO.NS": "^CNXFMCG",
    "PIDILITIND.NS": "^CNXFMCG",
    
    # Energy & Oil -> Nifty Energy
    "RELIANCE.NS": "^CNXENERGY", "ONGC.NS": "^CNXENERGY", "BPCL.NS": "^CNXENERGY",
    "NTPC.NS": "^CNXENERGY", "POWERGRID.NS": "^CNXENERGY", "ADANIPORTS.NS": "^CNXENERGY",
    "ADANIENT.NS": "^CNXENERGY",
    
    # Realty -> Nifty Realty
    "DLF.NS": "^CNXREALTY", "LODHA.NS": "^CNXREALTY",
    
    # Infrastructure & Capital Goods -> Nifty Infra
    "LT.NS": "^CNXINFRA", "SIEMENS.NS": "^CNXINFRA", "ABB.NS": "^CNXINFRA",
    "CUMMINSIND.NS": "^CNXINFRA", "BOSCHLTD.NS": "^CNXINFRA", "HAL.NS": "^CNXINFRA",
    "BEL.NS": "^CNXINFRA", "CGPOWER.NS": "^CNXINFRA",
    
    # Cement -> Use Nifty Infra as proxy
    "ULTRACEMCO.NS": "^CNXINFRA", "SHREECEM.NS": "^CNXINFRA", "AMBUJACEM.NS": "^CNXINFRA",
    "ACC.NS": "^CNXINFRA", "DALBHARAT.NS": "^CNXINFRA", "GRASIM.NS": "^CNXINFRA",
    
    # Consumer Discretionary / Retail
    "TITAN.NS": "^CNXFMCG", "TRENT.NS": "^CNXFMCG", "PAGEIND.NS": "^CNXFMCG",
    "ASIANPAINT.NS": "^CNXFMCG", "BERGEPAINT.NS": "^CNXFMCG",
    "VOLTAS.NS": "^CNXFMCG", "HAVELLS.NS": "^CNXFMCG", "ASTRAL.NS": "^CNXFMCG",
    
    # Telecom
    "BHARTIARTL.NS": "^CNXIT", "TATACOMM.NS": "^CNXIT",
    
    # Misc
    "INDHOTEL.NS": "^CNXFMCG", "SRF.NS": "^CNXINFRA", "POLYCAB.NS": "^CNXINFRA",
    "KEI.NS": "^CNXINFRA", "UPL.NS": "^CNXFMCG",
}

# Unique sector indices to download
SECTOR_INDICES = list(set(SECTOR_MAP.values()))
