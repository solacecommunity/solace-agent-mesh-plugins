import logging
from typing import Any, Dict, Optional

from google.adk.tools import ToolContext
import yfinance as yf

log = logging.getLogger(__name__)


async def get_stock_price(
    symbol: str,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get current stock price and trading information for a given symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "TSLA", "MSFT")

    Returns:
        Current price, day change, volume, and 52-week range
    """
    plugin_name = "finance"
    log_identifier = f"[{plugin_name}:get_stock_price]"
    log.info(f"{log_identifier} Fetching price data for symbol: {symbol}")

    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        # Check if we got valid data
        if not info or info.get("regularMarketPrice") is None:
            log.warning(f"{log_identifier} Invalid or unknown symbol: {symbol}")
            return {
                "status": "error",
                "message": f"Invalid or unknown symbol: {symbol}",
            }

        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        change = None
        change_percent = None
        if current_price and previous_close:
            change = round(current_price - previous_close, 2)
            change_percent = round((change / previous_close) * 100, 2)

        result = {
            "status": "success",
            "symbol": symbol.upper(),
            "current_price": current_price,
            "previous_close": previous_close,
            "change": change,
            "change_percent": change_percent,
            "day_high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
            "day_low": info.get("dayLow") or info.get("regularMarketDayLow"),
            "volume": info.get("volume") or info.get("regularMarketVolume"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        }

        log.info(f"{log_identifier} Successfully fetched price for {symbol}: ${current_price}")
        return result

    except Exception as e:
        log.exception(f"{log_identifier} Error fetching stock price for {symbol}: {e}")
        return {
            "status": "error",
            "message": f"Error fetching stock price for {symbol}: {str(e)}",
        }


async def get_stock_fundamentals(
    symbol: str,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Get fundamental financial metrics for a stock.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "TSLA", "MSFT")

    Returns:
        Key financial metrics including P/E ratio, market cap, EPS,
        dividend yield, revenue, profit margins, and debt-to-equity ratio
    """
    plugin_name = "finance"
    log_identifier = f"[{plugin_name}:get_stock_fundamentals]"
    log.info(f"{log_identifier} Fetching fundamentals for symbol: {symbol}")

    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        # Check if we got valid data
        if not info or not info.get("shortName"):
            log.warning(f"{log_identifier} Invalid or unknown symbol: {symbol}")
            return {
                "status": "error",
                "message": f"Invalid or unknown symbol: {symbol}",
            }

        result = {
            "status": "success",
            "symbol": symbol.upper(),
            "company_name": info.get("shortName") or info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "ex_dividend_date": info.get("exDividendDate"),
            "revenue": info.get("totalRevenue"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "book_value": info.get("bookValue"),
        }

        log.info(f"{log_identifier} Successfully fetched fundamentals for {symbol}")
        return result

    except Exception as e:
        log.exception(f"{log_identifier} Error fetching fundamentals for {symbol}: {e}")
        return {
            "status": "error",
            "message": f"Error fetching fundamentals for {symbol}: {str(e)}",
        }
