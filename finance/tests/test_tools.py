import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from finance.tools import get_stock_price, get_stock_fundamentals


@pytest.mark.asyncio
async def test_get_stock_price_valid_symbol():
    """Test get_stock_price with a valid symbol."""
    result = await get_stock_price("AAPL")

    assert result["status"] == "success"
    assert result["symbol"] == "AAPL"
    assert "current_price" in result
    assert isinstance(result["current_price"], (int, float))
    assert "previous_close" in result
    assert "change" in result
    assert "change_percent" in result
    assert "volume" in result
    assert "fifty_two_week_high" in result
    assert "fifty_two_week_low" in result


@pytest.mark.asyncio
async def test_get_stock_price_lowercase_symbol():
    """Test that lowercase symbols are converted to uppercase."""
    result = await get_stock_price("msft")

    assert result["status"] == "success"
    assert result["symbol"] == "MSFT"


@pytest.mark.asyncio
async def test_get_stock_price_invalid_symbol():
    """Test get_stock_price with an invalid symbol."""
    result = await get_stock_price("INVALIDXYZ123")

    assert result["status"] == "error"
    assert "message" in result
    assert "Invalid" in result["message"] or "Error" in result["message"]


@pytest.mark.asyncio
async def test_get_stock_fundamentals_valid_symbol():
    """Test get_stock_fundamentals with a valid symbol."""
    result = await get_stock_fundamentals("AAPL")

    assert result["status"] == "success"
    assert result["symbol"] == "AAPL"
    assert "company_name" in result
    assert "sector" in result
    assert "industry" in result
    assert "market_cap" in result
    assert "pe_ratio" in result
    assert "eps" in result
    assert "dividend_yield" in result
    assert "revenue" in result
    assert "profit_margin" in result
    assert "debt_to_equity" in result


@pytest.mark.asyncio
async def test_get_stock_fundamentals_lowercase_symbol():
    """Test that lowercase symbols are converted to uppercase."""
    result = await get_stock_fundamentals("googl")

    assert result["status"] == "success"
    assert result["symbol"] == "GOOGL"


@pytest.mark.asyncio
async def test_get_stock_fundamentals_invalid_symbol():
    """Test get_stock_fundamentals with an invalid symbol."""
    result = await get_stock_fundamentals("INVALIDXYZ123")

    assert result["status"] == "error"
    assert "message" in result
    assert "Invalid" in result["message"] or "Error" in result["message"]


@pytest.mark.asyncio
async def test_get_stock_price_returns_numeric_values():
    """Test that price values are numeric."""
    result = await get_stock_price("TSLA")

    if result["status"] == "success":
        assert isinstance(result["current_price"], (int, float, type(None)))
        assert isinstance(result["previous_close"], (int, float, type(None)))
        assert isinstance(result["volume"], (int, float, type(None)))


@pytest.mark.asyncio
async def test_get_stock_fundamentals_returns_company_info():
    """Test that fundamentals include company information."""
    result = await get_stock_fundamentals("MSFT")

    if result["status"] == "success":
        assert result["company_name"] is not None
        assert len(result["company_name"]) > 0
