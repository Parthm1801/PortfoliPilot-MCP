import requests
from datetime import datetime
from fastmcp import FastMCP
import os

# Replace with your actual NewsData.io API key
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "pub_87867e23b301f76d682d0db56d14879853324")

# Initialize the FastMCP server
mcp = FastMCP("News MCP Server")

@mcp.tool()
def get_latest_news(symbols: list[str]) -> dict:
    """
    Fetch the latest business news headlines for the given stock symbols
    from Indian sources using NewsData.io.
    """
    all_articles = []
    base_url = "https://newsdata.io/api/1/news"

    for symbol in symbols:
        # Derive a keyword from the symbol for search (e.g., INFY.NS → INFY)
        query = symbol.split(".")[0]

        params = {
            "apikey": NEWSDATA_API_KEY,
            "q": query,
            "country": "in",
            "category": "business",
            "language": "en"
        }

        try:
            response = requests.get(base_url, params=params)
            data = response.json()
            articles = data.get("results", [])

            for a in articles[:3]:  # top 3 articles per symbol
                all_articles.append({
                    "symbol": symbol,
                    "title": a.get("title"),
                    "summary": a.get("description", "")[:300],
                    "url": a.get("link"),
                    "published": a.get("pubDate")
                })

        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            continue

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "news_snapshot_date": datetime.utcnow().strftime('%Y-%m-%d'),
        "articles": all_articles
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")