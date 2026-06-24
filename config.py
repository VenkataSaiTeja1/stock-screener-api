"""Configuration and constants for Stock Screener"""

import pytz
from datetime import datetime

# Market Configurations
#
# NIFTY500_STOCKS: ~500 NSE-listed symbols (Nifty 500 universe), sourced from
# a community-maintained ticker list and de-duplicated/validated (no spaces,
# no stale/delisted-looking symbols). Yahoo Finance ticker format: SYMBOL.NS
#
# NYSE_STOCKS: ~500 US-listed symbols, using the S&P 500 constituent list
# (sourced from Wikipedia via the `datasets/s-and-p-500-companies` dataset)
# as the screening universe. Yahoo Finance format uses '-' instead of '.'
# for share classes (e.g. BRK.B -> BRK-B).
#
# NOTE: Index membership changes over time (mergers, delistings, rebalances).
# These lists are a good-enough working universe for screening, but if you
# notice a ticker that's clearly wrong/delisted, the screener already
# handles that gracefully (it's just skipped and logged) -- no need to
# treat missing data on a handful of symbols as a bug.

NIFTY500_STOCKS = [
    'ABB.NS', 'ACC.NS', 'ADANIENT.NS', 'ADANIGREEN.NS', 'ADANIPORTS.NS', 'ADANIPOWER.NS', 
    'AMBUJACEM.NS', 'APOLLOHOSP.NS', 'ASIANPAINT.NS', 'AUBANK.NS', 'AXISBANK.NS', 
    'BAJAJ-AUTO.NS', 'BAJAJFINSV.NS', 'BAJFINANCE.NS', 'BALKRISIND.NS', 'BANDHANBNK.NS', 
    'BANKBARODA.NS', 'BANKINDIA.NS', 'BEL.NS', 'BERGEPAINT.NS', 'BHARATFORG.NS', 
    'BHARTIARTL.NS', 'BHEL.NS', 'BIOCON.NS', 'BOSCHLTD.NS', 'BPCL.NS', 'BRITANNIA.NS', 
    'BSE.NS', 'CANBK.NS', 'CHOLAFIN.NS', 'CIPLA.NS', 'COALINDIA.NS', 'COCHINSHIP.NS', 
    'COFORGE.NS', 'COLPAL.NS', 'CONCOR.NS', 'COROMANDEL.NS', 'CROMPTON.NS', 'CUMMINSIND.NS', 
    'DABUR.NS', 'DALBHARAT.NS', 'DEEPAKNTR.NS', 'DELHIVERY.NS', 'DIVISLAB.NS', 'DIXON.NS', 
    'DLF.NS', 'DMART.NS', 'DRREDDY.NS', 'EICHERMOT.NS', 'ESCORTS.NS', 'EXIDEIND.NS', 
    'FEDERALBNK.NS', 'GAIL.NS', 'GLENMARK.NS', 'GMRINFRA.NS', 'GODREJCP.NS', 'GODREJPROP.NS', 
    'GRASIM.NS', 'GUJGASLTD.NS', 'HAL.NS', 'HAVELLS.NS', 'HCLTECH.NS', 'HDFCAMC.NS', 
    'HDFCBANK.NS', 'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS', 'HINDPETRO.NS', 
    'HINDUNILVR.NS', 'HINDZINC.NS', 'ICICIBANK.NS', 'ICICIGI.NS', 'ICICIPRULI.NS', 
    'IDFCFIRSTB.NS', 'IEX.NS', 'IGL.NS', 'INDHOTEL.NS', 'INDIAMART.NS', 'INDIGO.NS', 
    'INDUSINDBK.NS', 'INDUSTOWER.NS', 'INFY.NS', 'IOC.NS', 'IRB.NS', 'IRCTC.NS', 'IRFC.NS', 
    'ITC.NS', 'JINDALSTEL.NS', 'JSWENERGY.NS', 'JSWSTEEL.NS', 'JUBLFOOD.NS', 'KOTAKBANK.NS', 
    'KPITTECH.NS', 'L&TFH.NS', 'LALPATHLAB.NS', 'LAURUSLABS.NS', 'LICHSGFIN.NS', 'LICI.NS', 
    'LT.NS', 'LTIM.NS', 'LTTS.NS', 'LUPIN.NS', 'M&M.NS', 'M&MFIN.NS', 'MANAPPURAM.NS', 
    'MARICO.NS', 'MARUTI.NS', 'MAXHEALTH.NS', 'MAZDOCK.NS', 'MCX.NS', 'METROPOLIS.NS', 
    'MFSL.NS', 'MGL.NS', 'MOTHERSON.NS', 'MPHASIS.NS', 'MRF.NS', 'MUTHOOTFIN.NS', 
    'NATIONALUM.NS', 'NAUKRI.NS', 'NAVINFLUOR.NS', 'NMDC.NS', 'NTPC.NS', 'NYKAA.NS', 
    'OBEROIRLTY.NS', 'OIL.NS', 'ONGC.NS', 'PAGEIND.NS', 'PATANJALI.NS', 'PAYTM.NS', 
    'PEL.NS', 'PERSISTENT.NS', 'PETRONET.NS', 'PFC.NS', 'PIDILITIND.NS', 'PIIND.NS', 
    'PNB.NS', 'POLYCAB.NS', 'POONAWALLA.NS', 'POWERGRID.NS', 'PRESTIGE.NS', 'PVRINOX.NS', 
    'RAMCOCEM.NS', 'RBLBANK.NS', 'RECLTD.NS', 'RELIANCE.NS', 'RVNL.NS', 'SAIL.NS', 
    'SBICARD.NS', 'SBILIFE.NS', 'SBIN.NS', 'SCHAEFFLER.NS', 'SHREECEM.NS', 'SHRIRAMFIN.NS', 
    'SIEMENS.NS', 'SJVN.NS', 'SONACOMS.NS', 'SRF.NS', 'STARHEALTH.NS', 'SUNPHARMA.NS', 
    'SUNTV.NS', 'SUPREMEIND.NS', 'SUZLON.NS', 'SYNGENE.NS', 'TATACHEM.NS', 'TATACOMM.NS', 
    'TATACONSUM.NS', 'TATAELXSI.NS', 'TATAMOTORS.NS', 'TATAPOWER.NS', 'TATASTEEL.NS', 
    'TCS.NS', 'TECHM.NS', 'THERMAX.NS', 'TITAN.NS', 'TORNTPHARM.NS', 'TORNTPOWER.NS', 
    'TRENT.NS', 'TVSMOTOR.NS', 'UBL.NS', 'ULTRACEMCO.NS', 'UNIONBANK.NS', 'UPL.NS', 
    'VBL.NS', 'VEDL.NS', 'VOLTAS.NS', 'WIPRO.NS', 'YESBANK.NS', 'ZEEL.NS', 'ZOMATO.NS', 
    'ZYDUSLIFE.NS', 'AARTIIND.NS', 'ABFRL.NS', 'APOLLOTYRE.NS', 'ASHOKLEY.NS', 'ASTRAL.NS', 
    'BALRAMCHIN.NS', 'BATAINDIA.NS', 'BIKAJI.NS', 'CERA.NS', 'CGPOWER.NS', 'CHAMBLFERT.NS'
]

NYSE_STOCKS = [
    'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'AMD', 'AMZN', 'ASML', 'AVGO', 'AXP', 
    'BA', 'BAC', 'BKNG', 'BLK', 'BMY', 'BRK-B', 'C', 'CAT', 'CB', 'CI', 'CMCSA', 
    'CME', 'CMG', 'COP', 'COST', 'CRM', 'CSCO', 'CVS', 'CVX', 'DHR', 'DIS', 'ELV', 
    'FI', 'GE', 'GILD', 'GOOG', 'GOOGL', 'GS', 'HD', 'HON', 'IBM', 'INTC', 'INTU', 
    'ISRG', 'JNJ', 'JPM', 'KLAC', 'KO', 'LIN', 'LLY', 'LMT', 'LRCX', 'MA', 'MCD', 
    'MDLZ', 'MDT', 'META', 'MMC', 'MMM', 'MO', 'MRK', 'MS', 'MSFT', 'NEE', 'NFLX', 
    'NKE', 'NOW', 'NVDA', 'ORCL', 'PANW', 'PEP', 'PFE', 'PG', 'PGR', 'PH', 'PLD', 
    'PM', 'PNC', 'QCOM', 'REGN', 'RTX', 'SBUX', 'SCHW', 'SLB', 'SO', 'SPGI', 'SYK', 
    'T', 'TGT', 'TJX', 'TMO', 'TMUS', 'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'USB', 
    'V', 'VRTX', 'VZ', 'WFC', 'WM', 'WMT', 'XOM', 'AIG', 'AON', 'AEP', 'ADI', 'APD', 
    'BDX', 'BSX', 'BIIB', 'CARR', 'CTSH', 'CHTR', 'CL', 'COF', 'CRWD', 'DD', 'DE', 
    'DOW', 'DUK', 'EA', 'ECL', 'EMR', 'EOG', 'EPAM', 'EQIX', 'ETN', 'EW', 'EXC', 
    'FANG', 'FAST', 'FCX', 'FDX', 'FIS', 'FSLR', 'FTNT', 'GD', 'GIS', 'GLW', 'GM', 
    'HAL', 'HCA', 'HES', 'HLT', 'HPE', 'HPQ', 'HUM', 'ICE', 'IQV', 'ITW', 'KHC', 
    'KMI', 'KR', 'LHX', 'LOW', 'LUV', 'LYB', 'MAR', 'MCK', 'MCO', 'MET', 'MGM', 
    'MPC', 'MRNA', 'MSI', 'MU', 'NCLH', 'NEM', 'NOC', 'NSC', 'NXPI', 'O', 'OKE', 
    'ON', 'OXY', 'PAYX', 'PCAR', 'PEG', 'PPG', 'PRU', 'PSA', 'PSX', 'PYPL', 'RCL', 
    'ROST', 'SHW', 'SNA', 'SNPS', 'STZ', 'SYY', 'TEL', 'TRV', 'TT', 'UAL', 'UBER', 
    'URI', 'VLO', 'WBA', 'WBD', 'ZTS', 'AAL', 'BBY', 'CAH', 'CCL', 'DAL', 'EBAY', 
    'EXPE', 'HAS', 'K', 'LVS'
]


# Screening Criteria
FILTERS = {
    'PE_RATIO_MAX': 20,
    'VOLUME_RATIO_MIN': 2.0,
    'RSI_MIN': 50,
    'RSI_PERIOD': 14,
}

# Data Fetching Parameters
DATA_CONFIG = {
    'PERIOD': '120d',  # 120 days of historical data
    'INTERVAL': '1d',  # Daily interval
    'CACHE_TTL': 300,  # 5 minutes in seconds
    # Delay between requests. Bumped from 0.1s -> 0.3s now that the universe
    # is ~500 tickers per market: each ticker makes 2 network calls (price
    # history + .info), so 500 stocks is already ~1000 requests. A longer
    # delay reduces the chance of Yahoo rate-limiting mid-scan, which shows
    # up as a wave of "possibly delisted" / "No data" errors for tickers
    # that are actually fine.
    'REQUEST_DELAY': 0.3,
}

# Market Hours (IST for NSE, EST for NYSE)
MARKET_HOURS = {
    'NSE': {
        'timezone': 'Asia/Kolkata',
        'open': '09:15',
        'close': '15:30',
        'weekday_range': (0, 4)  # Monday to Friday
    },
    'NYSE': {
        'timezone': 'US/Eastern',
        'open': '09:30',
        'close': '16:00',
        'weekday_range': (0, 4)  # Monday to Friday
    }
}

# Scoring Weights for Ranking
SCORING_WEIGHTS = {
    'volume_ratio': 0.3,
    'rsi': 0.4,
    'pe_ratio': 0.3,
}

# UI Configuration
UI_CONFIG = {
    'MAX_DISPLAY': 15,  # Top 15 results
    'DECIMAL_PLACES': 2,
}

def get_ist_time():
    """Get current time in IST"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def get_est_time():
    """Get current time in EST"""
    est = pytz.timezone('US/Eastern')
    return datetime.now(est)