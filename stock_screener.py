"""Stock Screening Logic Module"""

import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
import time
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import json
import os

from config import (
    FILTERS, DATA_CONFIG, SCORING_WEIGHTS, 
    MARKET_HOURS, get_ist_time, get_est_time
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockScreener:
    """Main stock screening engine"""
    
    def __init__(self, market: str = 'NSE'):
        """
        Initialize screener
        
        Args:
            market: 'NSE' or 'NYSE'
        """
        self.market = market
        self.cache_dir = './cache'
        self.ensure_cache_dir()
        
    def ensure_cache_dir(self):
        """Ensure cache directory exists"""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def fetch_stock_data(self, ticker: str, period: str = '120d', 
                        interval: str = '1d') -> Optional[pd.DataFrame]:
        """
        Fetch stock data with error handling
        
        Args:
            ticker: Stock ticker symbol
            period: Period for historical data
            interval: Interval (1d, 1h, etc.)
            
        Returns:
            DataFrame or None if fetch fails
        """
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
                group_by='ticker',  # makes single-ticker downloads predictable too
                threads=False,
            )

            if data is None or data.empty:
                logger.warning(f"No data for {ticker}")
                return None

            # yfinance can return a MultiIndex on columns even for a single
            # ticker (e.g. ('Close', 'AAPL')). Flatten it before anything else.
            if isinstance(data.columns, pd.MultiIndex):
                # Most common shapes: (field, ticker) or (ticker, field)
                level0 = data.columns.get_level_values(0)
                level1 = data.columns.get_level_values(1)
                known_fields = {'open', 'high', 'low', 'close', 'adj close', 'volume'}

                if set(level0.str.lower()) <= known_fields:
                    # (field, ticker) -> keep field level
                    data.columns = level0
                elif set(level1.str.lower()) <= known_fields:
                    # (ticker, field) -> keep field level
                    data.columns = level1
                else:
                    # Fallback: just drop the ticker level positionally
                    data.columns = data.columns.droplevel(-1)

            # Ensure columns are lowercase strings
            data.columns = [str(c).lower() for c in data.columns]

            # De-duplicate any repeated columns that can appear after flattening
            data = data.loc[:, ~data.columns.duplicated()]

            if data.empty or 'close' not in data.columns:
                logger.warning(f"No usable price data for {ticker}")
                return None

            return data

        except Exception as e:
            logger.warning(f"Error fetching {ticker}: {str(e)}")
            return None
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Dictionary of indicators
        """
        try:
            indicators = {}
            
            # RSI Calculation
            if len(data) >= FILTERS['RSI_PERIOD']:
                rsi = ta.rsi(data['close'], length=FILTERS['RSI_PERIOD'])
                indicators['rsi'] = rsi.iloc[-1] if not rsi.empty else None
            else:
                indicators['rsi'] = None
            
            # Volume Ratio (current volume / 20-day average)
            if len(data) >= 20:
                vol_avg_20 = data['volume'].tail(20).mean()
                current_vol = data['volume'].iloc[-1]
                indicators['volume_ratio'] = current_vol / vol_avg_20 if vol_avg_20 > 0 else 0
            else:
                indicators['volume_ratio'] = 0
            
            # Price data
            indicators['current_price'] = data['close'].iloc[-1]
            indicators['prev_close'] = data['close'].iloc[-2] if len(data) > 1 else data['close'].iloc[-1]
            
            return indicators
            
        except Exception as e:
            logger.warning(f"Error calculating indicators: {str(e)}")
            return {}
    
    def get_ticker_info(self, ticker: str) -> Dict:
        """
        Fetch .info once per ticker and pull out P/E + company info from it.
        Combines what used to be two separate network calls (get_pe_ratio +
        get_company_info) into one, since each yf.Ticker(...).info hit is a
        separate request and was doubling our rate-limit exposure.

        Args:
            ticker: Stock ticker

        Returns:
            Dict with keys: pe_ratio, name, sector
        """
        result = {'pe_ratio': None, 'name': 'N/A', 'sector': 'N/A'}
        try:
            stock = yf.Ticker(ticker)
            info = stock.info  # single network call

            if not info or len(info) <= 1:
                # Newer yfinance sometimes returns a near-empty dict
                # ({'trailingPegRatio': None}) on a throttled/failed request
                # instead of raising.
                logger.warning(f"Empty info payload for {ticker}")
                return result

            pe = info.get('trailingPE') or info.get('forwardPE')
            if pe and pe > 0:
                result['pe_ratio'] = pe

            result['name'] = info.get('longName') or info.get('shortName') or 'N/A'
            result['sector'] = info.get('sector', 'N/A')

        except Exception as e:
            logger.warning(f"Error getting info for {ticker}: {str(e)}")

        return result

    def get_pe_ratio(self, ticker: str) -> Optional[float]:
        """
        Get P/E ratio for a stock (kept for backward compatibility;
        prefer get_ticker_info to avoid duplicate network calls).

        Args:
            ticker: Stock ticker
            
        Returns:
            P/E ratio or None
        """
        return self.get_ticker_info(ticker)['pe_ratio']
    
    def get_company_info(self, ticker: str) -> Dict:
        """
        Get company information (kept for backward compatibility;
        prefer get_ticker_info to avoid duplicate network calls).

        Args:
            ticker: Stock ticker
            
        Returns:
            Dictionary with company info
        """
        info = self.get_ticker_info(ticker)
        return {'name': info['name'], 'sector': info['sector']}
    
    def apply_filters(self, stock_data: Dict) -> Tuple[bool, Dict]:
        """
        Apply screening filters to stock
        
        Args:
            stock_data: Dictionary with stock metrics
            
        Returns:
            Tuple of (passes_filters, metrics)
        """
        passes = True
        reasons = []
        
        # Filter 1: P/E Ratio
        if stock_data['pe_ratio'] is None:
            passes = False
            reasons.append("P/E N/A")
        elif stock_data['pe_ratio'] > FILTERS['PE_RATIO_MAX']:
            passes = False
            reasons.append(f"P/E > {FILTERS['PE_RATIO_MAX']}")
        
        # Filter 2: Volume Ratio
        if stock_data['volume_ratio'] < FILTERS['VOLUME_RATIO_MIN']:
            passes = False
            reasons.append(f"Vol Ratio < {FILTERS['VOLUME_RATIO_MIN']}")
        
        # Filter 3: RSI
        if stock_data['rsi'] is None:
            passes = False
            reasons.append("RSI N/A")
        elif stock_data['rsi'] <= FILTERS['RSI_MIN']:
            passes = False
            reasons.append(f"RSI <= {FILTERS['RSI_MIN']}")
        
        return passes, reasons
    
    def calculate_score(self, stock_data: Dict) -> float:
        """
        Calculate composite score for ranking
        
        Args:
            stock_data: Dictionary with stock metrics
            
        Returns:
            Composite score
        """
        score = 0
        
        # Volume Ratio Score (0-100, normalized to 0-5)
        vol_ratio = stock_data['volume_ratio']
        vol_score = min(100, (vol_ratio / FILTERS['VOLUME_RATIO_MIN']) * 50)
        
        # RSI Score (0-100, RSI is already 0-100)
        rsi = stock_data['rsi'] or 0
        rsi_score = rsi
        
        # P/E Score (lower is better, 0-100)
        pe = stock_data['pe_ratio'] or FILTERS['PE_RATIO_MAX']
        pe_score = max(0, 100 - (pe / FILTERS['PE_RATIO_MAX'] * 100))
        
        # Weighted score
        score = (
            SCORING_WEIGHTS['volume_ratio'] * vol_score +
            SCORING_WEIGHTS['rsi'] * rsi_score +
            SCORING_WEIGHTS['pe_ratio'] * pe_score
        )
        
        return round(score, 2)
    
    def screen_stocks(self, tickers: List[str], 
                     max_results: int = 15) -> Tuple[List[Dict], Dict]:
        """
        Screen multiple stocks
        
        Args:
            tickers: List of ticker symbols
            max_results: Maximum results to return
            
        Returns:
            Tuple of (filtered_stocks, statistics)
        """
        results = []
        all_stocks = []
        stats = {
            'scanned': 0,
            'pe_known': 0,
            'passed_filters': 0,
            'shown': 0,
        }
        
        logger.info(f"Screening {len(tickers)} stocks...")
        
        for idx, ticker in enumerate(tickers):
            stats['scanned'] += 1
            
            # Rate limiting
            time.sleep(DATA_CONFIG['REQUEST_DELAY'])
            
            # Show progress
            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(tickers)} stocks")
            
            # Fetch data
            data = self.fetch_stock_data(ticker, DATA_CONFIG['PERIOD'], 
                                        DATA_CONFIG['INTERVAL'])
            if data is None:
                continue
            
            # Calculate indicators
            indicators = self.calculate_indicators(data)
            if not indicators:
                continue
            
            # Get P/E ratio + company info in a single .info call
            ticker_info = self.get_ticker_info(ticker)
            pe_ratio = ticker_info['pe_ratio']
            if pe_ratio:
                stats['pe_known'] += 1
            
            company_info = {'name': ticker_info['name'], 'sector': ticker_info['sector']}
            
            # Compile stock data
            stock_data = {
                'ticker': ticker,
                'name': company_info['name'],
                'current_price': round(indicators['current_price'], 2),
                'pe_ratio': round(pe_ratio, 2) if pe_ratio else None,
                'volume_ratio': round(indicators['volume_ratio'], 2),
                'rsi': round(indicators['rsi'], 2) if indicators['rsi'] else None,
                'sector': company_info['sector'],
                'timestamp': datetime.now().isoformat(),
            }
            
            # Apply filters
            passes, reasons = self.apply_filters(stock_data)
            
            # Store all stocks
            stock_data['passes_filters'] = passes
            stock_data['filter_reasons'] = reasons

            # Every ticker we successfully fetched data for goes into
            # all_stocks, regardless of whether it passed filters. This is
            # what feeds the "all scanned tickers (pre-filter)" view.
            all_stocks.append(stock_data)
            
            if passes:
                stats['passed_filters'] += 1
                # Calculate score for ranking
                stock_data['score'] = self.calculate_score(stock_data)
                results.append(stock_data)
        
        # Sort by score and limit results
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        shown_results = results[:max_results]
        stats['shown'] = len(shown_results)
        
        logger.info(f"Screening complete. Passed filters: {stats['passed_filters']}")
        
        return shown_results, stats, all_stocks
    
    def get_market_status(self) -> Dict:
        """
        Get current market status
        
        Returns:
            Dictionary with market status
        """
        if self.market == 'NSE':
            current_time = get_ist_time()
            market_info = MARKET_HOURS['NSE']
        else:
            current_time = get_est_time()
            market_info = MARKET_HOURS['NYSE']
        
        # Parse market hours
        open_time = datetime.strptime(market_info['open'], '%H:%M').time()
        close_time = datetime.strptime(market_info['close'], '%H:%M').time()
        
        is_weekday = current_time.weekday() in market_info['weekday_range']
        is_open = is_weekday and open_time <= current_time.time() <= close_time
        
        return {
            'market': self.market,
            'is_open': is_open,
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': market_info['timezone'],
            'open_time': market_info['open'],
            'close_time': market_info['close'],
        }


def format_stock_results(stocks: List[Dict], all_stocks: List[Dict]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Format results into DataFrames for display
    
    Args:
        stocks: Top ranked stocks
        all_stocks: All stocks before final filtering
        
    Returns:
        Tuple of (top_df, all_df)
    """
    if stocks:
        top_df = pd.DataFrame([
            {
                'Rank': idx + 1,
                'Ticker': s['ticker'],
                'Name': s['name'][:40],  # Truncate long names
                'Price': f"₹{s['current_price']}" if '₹' in str(s['current_price']) else f"${s['current_price']}",
                'P/E': f"{s['pe_ratio']:.2f}" if s['pe_ratio'] else '—',
                'Vol Ratio': f"{s['volume_ratio']:.2f}x",
                'RSI': f"{s['rsi']:.1f}" if s['rsi'] else '—',
                'Score': f"{s['score']:.2f}",
            }
            for idx, s in enumerate(stocks)
        ])
    else:
        top_df = pd.DataFrame()
    
    if all_stocks:
        all_df = pd.DataFrame([
            {
                'Ticker': s['ticker'],
                'Name': s['name'][:40],
                'Price': f"₹{s['current_price']}" if '₹' in str(s['current_price']) else f"${s['current_price']}",
                'P/E': f"{s['pe_ratio']:.2f}" if s['pe_ratio'] else '—',
                'Vol Ratio': f"{s['volume_ratio']:.2f}x",
                'RSI': f"{s['rsi']:.1f}" if s['rsi'] else '—',
                'Status': '✓ Passed' if s['passes_filters'] else f"✗ {', '.join(s['filter_reasons'])}",
            }
            for s in all_stocks
        ])
    else:
        all_df = pd.DataFrame()
    
    return top_df, all_df