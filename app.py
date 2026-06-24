import os
import json
import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# Import the Stock Screener logic and configuration
from stock_screener import StockScreener, format_stock_results
from config import NIFTY500_STOCKS, NYSE_STOCKS

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def verify_and_clean_ticker(user_query):
    """
    Resolves natural language or messy strings to clean yfinance symbols.
    """
    clean_query = user_query.strip().upper()
    
    # Common routing overrides
    if "RELIANCE" in clean_query and not clean_query.endswith(".NS"):
        return "RELIANCE.NS"
    if "TCS" in clean_query and not clean_query.endswith(".NS"):
        return "TCS.NS"
    if "INFOSYS" in clean_query and not clean_query.endswith(".NS"):
        return "INFY.NS"
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"Resolve company name '{user_query}' to its exact Yahoo Finance ticker symbol. If Indian, append '.NS'. Return ONLY the plain ticker symbol without quotes or formatting."
        
        response = model.generate_content(prompt)
        resolved = response.text.strip().replace('"', '').replace("`", "")
        return resolved if resolved else clean_query
    except Exception as e:
        print(f"Ticker resolution error: {e}")
        return clean_query

@app.route("/api/search-ticker", methods=["POST"])
def search_ticker():
    """Provides local fast autocomplete routing hints."""
    data = request.json or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify([])
    
    mock_registry = [
        {"ticker": "AAPL", "name": "Apple Inc. (NYSE)"},
        {"ticker": "MSFT", "name": "Microsoft Corporation (NASDAQ)"},
        {"ticker": "GOOGL", "name": "Alphabet Inc. (NASDAQ)"},
        {"ticker": "RELIANCE.NS", "name": "Reliance Industries Ltd. (NSE)"},
        {"ticker": "TCS.NS", "name": "Tata Consultancy Services (NSE)"},
        {"ticker": "INFY.NS", "name": "Infosys Ltd. (NSE)"},
    ]
    
    filtered = [item for item in mock_registry if query.upper() in item["ticker"] or query.lower() in item["name"].lower()]
    return jsonify(filtered[:3])


@app.route("/api/screen", methods=["POST"])
def screen_market():
    """
    Broad Market Screener Endpoint
    Executes the StockScreener logic for Nifty 500 or S&P 500 based on the request.
    """
    data = request.json or {}
    market = data.get("market", "NSE").upper()
    
    if market not in ["NSE", "NYSE"]:
        return jsonify({"error": "Invalid market selected. Choose NSE or NYSE."}), 400

    try:
        print(f"\n🔍 Initiating broad market scan for: {market}")
        tickers = NIFTY500_STOCKS if market == 'NSE' else NYSE_STOCKS
        
        screener = StockScreener(market)
        
        # Execute the scan (this will take a few minutes as it pulls OHLCV for 500 stocks)
        top_stocks, stats, all_stocks = screener.screen_stocks(tickers, max_results=15)
        
        # Format the data using the provided helper function (CAPTURE BOTH NOW)
        top_df, all_df = format_stock_results(top_stocks, all_stocks)
        
        # Convert the Pandas DataFrames into JSON-serializable lists of dictionaries
        top_stocks_list = top_df.to_dict(orient="records")
        all_stocks_list = all_df.to_dict(orient="records")
        
        print(f"✅ Market scan complete! Passed filters: {stats.get('passed_filters', 0)}")
        
        return jsonify({
            "stats": stats,
            "top_stocks": top_stocks_list,
            "all_stocks": all_stocks_list
        })
        
    except Exception as e:
        print(f"Screener Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/analyze", methods=["POST"])
def analyze_stock():
    """
    AI Deep Analyzer Endpoint
    Fetches real-time yfinance snapshot and passes to Gemini LLM for 8-tab qualitative report.
    """
    data = request.json or {}
    user_query = data.get("query", "").strip()
    
    # Read the history timeframe option from the frontend (default to 5 if not sent)
    history_years = data.get("history_years", 5)
    
    if not user_query:
        return jsonify({"error": "Query cannot be blank"}), 400

    try:
        print(f"\n🚀 1. Resolving ticker for: {user_query}")
        ticker = verify_and_clean_ticker(user_query)
        print(f"✅ Resolved to: {ticker}")
        
        print(f"📊 2. Fetching quantitative data from yfinance (Timeframe: {history_years} years)...")
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
            if "." in ticker:
                ticker = ticker.split(".")[0]
                stock = yf.Ticker(ticker)
                info = stock.info
                
            if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                return jsonify({
                    "error": f"Symbol code '{ticker}' could not be validated by Yahoo Finance. Check spelling or market suffixes."
                }), 404

        print("✅ yfinance data retrieved!")

        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"
        currency = info.get("currency", "")
        
        yf_context = {
            "name": info.get("longName", ticker),
            "ticker": ticker,
            "currentPrice": f"{currency} {current_price}" if current_price != "N/A" else "N/A",
            "marketCap": info.get("marketCap", "N/A"),
            "peRatio": info.get("trailingPE", "N/A"),
            "dividendYield": info.get("dividendYield", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "summary": info.get("longBusinessSummary", "")[:600]
        }

        print(f"🧠 3. Sending data to Gemini (Enforced Window: {history_years} Years)...")
        
        # Converted to an f-string to pull the dynamic history_years parameter smoothly
        prompt = f"""
You are an expert institutional equity research analyst. Conduct a thorough 8-tab fundamental analysis for {yf_context['name']} ({yf_context['ticker']}).
Baseline Financial Profile: {json.dumps(yf_context)}

CRITICAL TIME PROFILE INSTRUCTION:
Your qualitative analysis, CAGR growth metric calculations, margin trends, management performance evaluations, and asset compounding trajectories MUST focus strictly on evaluating the past {history_years} years of historical trajectory data. Adjust all metrics, compounder returns summaries, and matrix tracking to align with this explicit {history_years}-year analysis macro window.

Utilize your knowledge engine to enrich this dataset. 
You must respond with a strictly valid JSON object matching the exact schema below.

{{
  "overview": {{
    "about": "Detailed summary of corporate strategy, core markets, and executive operations over the specified timeframe.",
    "currentPrice": "{yf_context['currentPrice']}",
    "marketCap": "Formatted currency string representing valuation",
    "peRatio": "{yf_context['peRatio']}",
    "dividendYield": "{yf_context['dividendYield']}"
  }},
  "valuation": {{
    "status": "UNDERVALUED | OVERVALUED | FAIR",
    "peMetric": "P/E relative tracking summary",
    "industryAvg": "Industry relative context",
    "matrixTable": [
      {{"metric": "P/E Ratio (TTM)", "current": "{yf_context['peRatio']}", "sector": "Target Peer Median Value", "historical": "{history_years}-Yr Average Value", "signal": "CHEAP | EXPENSIVE | FAIR"}}
    ]
  }},
  "growth": {{
    "revenueInsight": "Top-line performance tracking mechanics observed across the historical window.",
    "profitTrend": "Earnings capacity and net margin health evaluation over this period.",
    "marginAnalysis": "Operating profile changes and input cost tracking metrics."
  }},
  "health": {{
    "debtToEquity": "Leverage and risk profiling parameters.",
    "currentRatio": "Liquidity evaluation profile metrics.",
    "bullScenario": "Primary strategic levers driving unexpected upside moves.",
    "bearScenario": "Core macroeconomic headwinds or direct execution liabilities."
  }},
  "returns": {{
    "roe": "Return on Equity trend summary.",
    "roce": "Return on Capital Employed profile metrics.",
    "history": "Capital allocation strategy and compounder returns overview across the past {history_years} years."
  }},
  "peers": {{
    "list": ["Competitor 1", "Competitor 2", "Competitor 3"],
    "marketPosition": "Competitive positioning landscape and barriers to entry."
  }},
  "ownership": {{
    "promoters": "Insider holding structures and pledging trends.",
    "fii": "Foreign flows and institutional holding trends.",
    "dii": "Domestic structural demand support tracking.",
    "managementTone": "OPTIMISTIC | CAUTIOUS | STABLE with operational validation."
  }},
  "view": {{
    "verdict": "STRONG BUY | BUY | HOLD | AVOID",
    "strengths": ["Strategic asset capability", "Strong structural moat profile"],
    "risks": ["Regulatory exposures or macro hazards", "Execution risk vectors"],
    "watchPoints": ["Core parameters to observe next quarter"]
  }}
}}
"""
        model = genai.GenerativeModel("gemini-2.5-flash")
        analysis_response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        print("✅ Gemini response received!")
        
        structured_data = json.loads(analysis_response.text)
        return jsonify(structured_data)

    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")
        return jsonify({"error": "LLM returned an invalid JSON configuration structure. Please re-run search to re-verify."}), 502
    except Exception as e:
        print(f"General Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)