from flask import Flask, render_template
from dataservice import fetch_transaction_balances
from filter import filter_trades_by_addresses
from processing import calculate_stats, process_builder_trades
import time

app = Flask(__name__)

# Cache for API data
_data_cache = None
_cache_timestamp = None
CACHE_TTL = 300  # Cache for 5 minutes (300 seconds)


def load_data(force_refresh=False, use_cache_only=False):
    """
    Fetch data directly from the API and filter by addresses. Uses caching to avoid repeated API calls.
    
    Args:
        force_refresh: If True, always fetch fresh data from API
        use_cache_only: If True, only return cached data, never call API (for filtering operations)
    
    Returns:
        Cached data if available, or fresh data from API
    """
    global _data_cache, _cache_timestamp
    
    # If use_cache_only is True, only return cached data (never call API)
    if use_cache_only:
        if _data_cache is not None:
            age = time.time() - _cache_timestamp if _cache_timestamp else 0
            print(f"Using cached data for filtering (age: {age:.1f}s)")
            return _data_cache
        else:
            print("No cached data available for filtering")
            return None
    
    # Check if we have valid cached data
    if not force_refresh and _data_cache is not None and _cache_timestamp is not None:
        age = time.time() - _cache_timestamp
        if age < CACHE_TTL:
            print(f"Using cached data (age: {age:.1f}s)")
            return _data_cache
    
    # Fetch fresh data
    try:
        print("Fetching fresh data from API...")
        data = fetch_transaction_balances()
        if data:
            data = filter_trades_by_addresses(data)
            # Update cache
            _data_cache = data
            _cache_timestamp = time.time()
            print("Data cached successfully")
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        # If we have stale cache, use it as fallback
        if _data_cache is not None:
            print("Using stale cache as fallback")
            return _data_cache
        return None


def get_builder_trades(data, builder_address):
    """Get all trades for a specific builder address."""
    if not data or "data" not in data:
        return []
    
    if "EVM" not in data["data"] or not isinstance(data["data"]["EVM"], dict):
        return []
    
    trades = data["data"]["EVM"].get("DEXTrades", [])
    if not isinstance(trades, list):
        return []
    
    builder_address_lower = builder_address.lower()
    builder_trades = []
    
    for trade in trades:
        if not isinstance(trade, dict):
            continue
        
        # Check if this trade involves the builder
        raw_balances = trade.get("joinTransactionBalances")
        balance_joins = []
        
        if raw_balances is not None:
            if isinstance(raw_balances, list):
                balance_joins = raw_balances
            elif isinstance(raw_balances, dict):
                if "TokenBalance" in raw_balances:
                    balance_joins = [raw_balances]
                else:
                    balance_joins = [v for v in raw_balances.values() if isinstance(v, dict)]
        
        # Check if builder is involved in this trade
        builder_involved = False
        for balance_join in balance_joins:
            if not isinstance(balance_join, dict):
                continue
            token_balance = balance_join.get("TokenBalance", {})
            if not token_balance or not isinstance(token_balance, dict):
                continue
            address = token_balance.get("Address", "")
            if address.lower() == builder_address_lower:
                builder_involved = True
                break
        
        if builder_involved:
            builder_trades.append(trade)
    
    return builder_trades


@app.route("/")
def index():
    """Main dashboard route."""
    data = load_data()
    
    if data is None:
        return render_template("error.html", message="Could not fetch data from API")
    
    stats = calculate_stats(data)
    
    if stats is None:
        return render_template("error.html", message="Invalid data format from API")
    
    return render_template("dashboard.html", stats=stats)


@app.route("/refresh")
def refresh_cache():
    """Manually refresh the data cache."""
    data = load_data(force_refresh=True)
    if data is None:
        return render_template("error.html", message="Could not fetch data from API")
    return render_template("error.html", message="Cache refreshed successfully! <a href='/'>Go back to dashboard</a>")


@app.route("/builder/<address>")
def builder_trades(address):
    """Show individual trades for a specific builder. Only filters cached data, never calls API."""
    # use_cache_only=True means we ONLY use cached data, never make API calls
    data = load_data(use_cache_only=True)
    
    if data is None:
        return render_template("error.html", message="No cached data available. Please visit the <a href='/'>dashboard</a> first to load data.")
    
    trades = get_builder_trades(data, address)
    
    processed_trades = process_builder_trades(trades, address)
    
    return render_template("builder_trades.html", builder_address=address, trades=processed_trades)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

