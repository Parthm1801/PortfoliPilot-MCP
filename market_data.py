import yfinance as yf
from datetime import datetime
from fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("Market MCP Server")

# Define a tool to fetch market data
@mcp.tool()
def get_market_data(symbols: list[str]) -> dict:
    """
    Fetches current price and percentage change for given stock symbols.
    """
    snapshot = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            prev_close = info.get("previousClose")

            if price is None or prev_close is None:
                continue

            change_pct = ((price - prev_close) / prev_close) * 100

            snapshot.append({
                "symbol": symbol,
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2)
            })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            continue

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "market_snapshot_date": datetime.utcnow().strftime('%Y-%m-%d'),
        "symbols": snapshot
    }

# Run the MCP server
if __name__ == "__main__":
    # from pprint import pprint
    # pprint(get_market_data(["KDL-ST.NS"]))
    mcp.run(transport='stdio')
