import requests
import pickle
import time
from fastmcp import FastMCP
from pathlib import Path

# Initialize the FastMCP server
mcp = FastMCP("NSE MCP Server")


# Rate limiting - max 3 requests per second like NSE.py
class SimpleThrottle:
    def __init__(self, rps=3):
        self.rps = rps
        self.last_request_time = 0

    def check(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.rps

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()


throttle = SimpleThrottle(rps=3)

MARKET_TYPES = ["equities", "sme", "debt", "mf", "invitsreits"]

# Improved headers matching NSE.py approach
BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/118.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Referer': 'https://www.nseindia.com/get-quotes/equity?symbol=HDFCBANK',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

BASE_URL = "https://www.nseindia.com"
API_BASE_URL = "https://www.nseindia.com/api"

# Cookie management
COOKIE_FILE = Path("nse_cookies.pkl")

session = requests.Session()
session.headers.update(BASE_HEADERS)


def save_cookies(cookies):
    """Save cookies to file"""
    try:
        with open(COOKIE_FILE, 'wb') as f:
            pickle.dump(cookies, f)
    except Exception as e:
        print(f"Failed to save cookies: {e}")


def load_cookies():
    """Load cookies from file"""
    try:
        if COOKIE_FILE.exists():
            with open(COOKIE_FILE, 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        print(f"Failed to load cookies: {e}")
    return None


def are_cookies_expired(cookies):
    """Check if cookies are expired"""
    if not cookies:
        return True

    for cookie in cookies:
        if hasattr(cookie, 'is_expired') and cookie.is_expired():
            return True
    return False


def refresh_cookies():
    """Refresh NSE session cookies by visiting option-chain page"""
    try:
        print("Refreshing NSE cookies...")
        throttle.check()

        # Visit option-chain page to get fresh cookies (same as NSE.py)
        resp = session.get(f"{BASE_URL}/option-chain", timeout=15, allow_redirects=True)

        if resp.status_code != 200:
            raise Exception(f"Failed to get cookies. Status: {resp.status_code}")

        # Check if we got a valid NSE page
        if "nseindia" not in resp.text.lower():
            raise Exception("Unexpected response while refreshing NSE session.")

        # Save the new cookies
        save_cookies(session.cookies)
        print("Cookies refreshed successfully")

        return session.cookies

    except Exception as e:
        print(f"Failed to refresh NSE cookies: {e}")
        raise


def get_valid_cookies():
    """Get valid cookies, refresh if needed"""
    cookies = load_cookies()

    if cookies is None or are_cookies_expired(cookies):
        cookies = refresh_cookies()
    else:
        session.cookies.update(cookies)

    return cookies


def make_api_request(url, params=None):
    """Make API request with proper error handling and rate limiting"""
    try:
        # Ensure we have valid cookies
        get_valid_cookies()

        # Apply rate limiting
        throttle.check()

        # Make the request
        response = session.get(url, params=params, timeout=15)

        # Check for successful response
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401 or response.status_code == 403:
            # Unauthorized - refresh cookies and try once more
            print("Unauthorized response, refreshing cookies...")
            refresh_cookies()
            throttle.check()
            response = session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        else:
            response.raise_for_status()

    except Exception as e:
        print(f"API request failed for {url}: {e}")
        raise


# Initialize cookies on startup
get_valid_cookies()

def resolve_market(symbol: str, url_path: str, extra_params: dict = None) -> tuple[str, dict]:
    for market in MARKET_TYPES:
        try:
            url = f"{API_BASE_URL}/{url_path}"
            params = {
                "symbol": symbol.upper(),
                "market": market
            }
            if extra_params:
                params.update(extra_params)
            data = make_api_request(url, params)
            if data:  # if response is non-empty
                return market, data
        except Exception:
            continue
    return None, {"error": f"Could not resolve market for symbol {symbol}."}


@mcp.tool()
def get_stock_snapshot(symbol: str) -> dict:
    """
    Fetches current stock info for the given NSE symbol.
    """
    try:
        url = f"{API_BASE_URL}/quote-equity"
        params = {"symbol": symbol.upper()}
        return make_api_request(url, params)
    except Exception as e:
        return {"error": f"Failed to fetch stock data for {symbol}: {str(e)}"}

@mcp.tool()
def get_announcements(symbol: str, from_date: str, to_date: str) -> dict:
    """
    Fetch announcements like financials, earnings, acquisitions, or con calls.
    Date format: dd-mm-yyyy
    """
    extra_params = {
        "corpType": "announcement",
        "from_date": from_date,
        "to_date": to_date
    }
    market, data = resolve_market(symbol, "corporate-disclosure-getquote", extra_params)
    return data

@mcp.tool()
def get_event_calendar(symbol: str) -> dict:
    """
    Fetches event calendar like board meetings and financial result dates.
    """
    extra_params = {"corpType": "eventcalender"}
    market, data = resolve_market(symbol, "corp-info", extra_params)
    return data

@mcp.tool()
def get_users_name() -> dict:
    """
    Fetches current user-name when asked whoami
    :return: string name
    """
    return {"name": "Laude ka baal"}

@mcp.tool()
def get_market_status() -> dict:
    """
    Get current market status
    """
    try:
        url = f"{API_BASE_URL}/marketStatus"
        result = make_api_request(url)
        return result.get("marketState", result)
    except Exception as e:
        return {"error": f"Failed to fetch market status: {str(e)}"}


if __name__ == "__main__":
    # from pprint import pprint
    #
    # test_symbol = "KDL"
    # today = datetime.today()
    # from_date = "01-01-2025"
    # to_date = "25-05-2025"
    # market = "SME"
    #
    # print("--- Market Status ---")
    # pprint(get_market_status())

    # print("\n--- Stock Snapshot ---")
    # pprint(get_stock_snapshot(test_symbol))
    #
    # print("\n--- Announcements ---")
    # pprint(get_announcements(test_symbol, from_date, to_date ))
    #
    # print("\n--- Event Calendar ---")
    # pprint(get_event_calendar(test_symbol))

    # To run as MCP
    mcp.run(transport='stdio')