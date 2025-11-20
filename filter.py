from typing import Iterable, Optional

DEFAULT_ADDRESSES = [
    "0xf2f5c73fa04406b1995e397b55c24ab1f3ea726c",
    "0x036C9c0aaE7a8268F332bA968dac5963c6aDAca5",
    "0xf573d99385c05c23b24ed33de616ad16a43a0919",
    "0x000000000000d3B2C76221467d2f8c8f1dE832A2",
    "0x199D5ED7F45F4eE35960cF22EAde2076e95B253F",
    "0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97",
    "0xaab27b150451726ec7738aa1d0a94505c8729bd1",
    "0x57865ba267d48671a41431f471933aec32a7c7d1",
    "0x0000000000675d852C8638Df2f227949052b1208",
    "0xdadb0d80178819f2319190d340ce9a924f783711",
    "0x4675c7e5baafbffbca748158becba61ef3b0a263",
    "0x396343362be2a4da1ce0c1c210945346fb82aa49"
]


def filter_trades_by_addresses(
    data: dict, addresses: Optional[Iterable[str]] = None
) -> dict:
    """
    Filter DEXTrades to only include those where TokenBalance.Address matches the provided addresses.
    
    Args:
        data: The API response data containing DEXTrades
        addresses: Optional list of addresses to filter by. If None, uses DEFAULT_ADDRESSES.
    
    Returns:
        The data dict with filtered DEXTrades
    """
    if not data or "data" not in data:
        return data
    
    if "EVM" not in data["data"] or not isinstance(data["data"]["EVM"], dict):
        return data
    
    filter_addresses = {addr.lower() for addr in (addresses or DEFAULT_ADDRESSES)}
    
    if "DEXTrades" not in data["data"]["EVM"]:
        data["data"]["EVM"]["DEXTrades"] = []
        return data
    
    trades = data["data"]["EVM"]["DEXTrades"]
    if not isinstance(trades, list):
        trades = []
    
    filtered_trades = []
    
    for trade in trades:
        if not isinstance(trade, dict):
            continue
        # Check if any TokenBalance.Address in joinTransactionBalances matches our addresses
        if "joinTransactionBalances" in trade:
            balance_joins = trade["joinTransactionBalances"]
            
            # Handle both list and dict formats
            balance_items = []
            if isinstance(balance_joins, list):
                balance_items = balance_joins
            elif isinstance(balance_joins, dict):
                # If it's a dict, it might be a single item or have nested structure
                # Check if it has TokenBalance directly
                if "TokenBalance" in balance_joins:
                    balance_items = [balance_joins]
                else:
                    # Try to extract items from dict values
                    balance_items = [v for v in balance_joins.values() if isinstance(v, dict)]
            
            if len(balance_items) > 0:
                found_match = False
                for balance_join in balance_items:
                    if isinstance(balance_join, dict) and "TokenBalance" in balance_join:
                        token_balance = balance_join["TokenBalance"]
                        if isinstance(token_balance, dict):
                            token_address = token_balance.get("Address", "")
                            if token_address:
                                token_address_lower = token_address.lower()
                                if token_address_lower in filter_addresses:
                                    filtered_trades.append(trade)
                                    found_match = True
                                    break
                if not found_match:
                    continue
    
    data["data"]["EVM"]["DEXTrades"] = filtered_trades
    return data

