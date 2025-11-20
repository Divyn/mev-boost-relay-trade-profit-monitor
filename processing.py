from collections import defaultdict
from filter import DEFAULT_ADDRESSES


def calculate_stats(data):
    """Calculate statistics from the DEXTrades data, organized by block builder."""
    if not data:
        return None
    
    if not isinstance(data, dict):
        return None
    
    if "data" not in data:
        return None
    
    if not isinstance(data["data"], dict):
        return None
    
    if "EVM" not in data["data"]:
        return None
    
    if not isinstance(data["data"]["EVM"], dict):
        return None

    trades = data["data"]["EVM"].get("DEXTrades", [])
    if not isinstance(trades, list):
        trades = []
    
    # Track MEV builder addresses (the filtered addresses)
    mev_builder_addresses = {addr.lower() for addr in DEFAULT_ADDRESSES}
    # Map lowercase to original address for display
    mev_builder_address_map = {addr.lower(): addr for addr in DEFAULT_ADDRESSES}
    
    # Structure: builder_address -> block_number -> block summary
    builder_blocks = defaultdict(lambda: defaultdict(lambda: {
        "block_number": "",
        "block_time": "",
        "total_profit_usd": 0.0,
        "total_balance_change": 0.0,
        "transaction_count": 0,
        "tokens": defaultdict(lambda: {"balance_change": 0.0, "profit_usd": 0.0}),
    }))
    
    stats = {
        "total_transactions": len(trades),
        "total_value_usd": 0,
        "total_balance_change": 0,
        "unique_addresses": set(),
        "transactions_by_address": defaultdict(int),
        "balance_change_by_address": defaultdict(float),
        "transactions_by_reason": defaultdict(int),
        "date_range": {"earliest": None, "latest": None},
        "balance_changes": {"increases": 0, "decreases": 0},
        "unique_blocks": set(),
        "dex_protocols": defaultdict(int),
    }

    for trade in trades:
        if not isinstance(trade, dict):
            continue
        # Get transaction info
        transaction = trade.get("Transaction", {}) or {}
        block = trade.get("Block", {}) or {}
        trade_info = trade.get("Trade", {}) or {}
        fee_info = trade.get("Fee", {}) or {}
        
        block_number = block.get("Number", "")
        block_time = block.get("Time", "")
        
        # Process joinTransactionBalances to get token balance changes
        # Handle the same formats as the filter (list, dict, etc.)
        raw_balances = trade.get("joinTransactionBalances")
        balance_joins = []
        
        if raw_balances is not None:
            if isinstance(raw_balances, list):
                balance_joins = raw_balances
            elif isinstance(raw_balances, dict):
                # Check if it has TokenBalance directly (single item)
                if "TokenBalance" in raw_balances:
                    balance_joins = [raw_balances]
                else:
                    # Try to extract items from dict values
                    balance_joins = [v for v in raw_balances.values() if isinstance(v, dict)]
        
        # Calculate total value from trade
        buy_info = trade_info.get("Buy", {}) or {}
        sell_info = trade_info.get("Sell", {}) or {}
        if not isinstance(buy_info, dict):
            buy_info = {}
        if not isinstance(sell_info, dict):
            sell_info = {}
        buy_amount_usd = float(buy_info.get("AmountInUSD", 0) or 0)
        sell_amount_usd = float(sell_info.get("AmountInUSD", 0) or 0)
        trade_value_usd = max(buy_amount_usd, sell_amount_usd)
        stats["total_value_usd"] += trade_value_usd

        # DEX protocol tracking
        dex_info = trade_info.get("Dex", {}) or {}
        if not isinstance(dex_info, dict):
            dex_info = {}
        protocol_name = dex_info.get("ProtocolName", "Unknown")
        stats["dex_protocols"][protocol_name] += 1

        # Process each token balance in the trade
        builder_address_lower = None
        for balance_join in balance_joins:
            if not isinstance(balance_join, dict):
                continue
            token_balance = balance_join.get("TokenBalance", {})
            if not token_balance or not isinstance(token_balance, dict):
                continue
                
            # Calculate balance change (post-pre)
            pre_balance = float(token_balance.get("PreBalance", 0) or 0)
            post_balance = float(token_balance.get("PostBalance", 0) or 0)
            balance_change = post_balance - pre_balance
            
            # Calculate USD profit if available
            pre_balance_usd = float(token_balance.get("PreBalanceInUSD", 0) or 0)
            post_balance_usd = float(token_balance.get("PostBalanceInUSD", 0) or 0)
            profit_usd = post_balance_usd - pre_balance_usd
            
            # Get currency info
            currency = token_balance.get("Currency", {}) or {}
            if not isinstance(currency, dict):
                currency = {}
            currency_name = currency.get("Name", "Unknown")
            currency_symbol = currency.get("Symbol", "")
            
            # Unique addresses
            address = token_balance.get("Address", "")
            address_lower = address.lower() if address else ""
            
            # Check if this is an MEV builder address
            is_mev_builder = address_lower in mev_builder_addresses
            
            # Track the builder address for this trade (use first MEV builder found)
            if is_mev_builder and builder_address_lower is None:
                builder_address_lower = address_lower
            
            if address:
                stats["unique_addresses"].add(address)
                stats["transactions_by_address"][address] += 1
                stats["balance_change_by_address"][address] += balance_change

            # Balance change reason codes
            reason_code = token_balance.get("BalanceChangeReasonCode")
            if reason_code is not None:
                stats["transactions_by_reason"][reason_code] += 1

            # Balance changes
            if post_balance > pre_balance:
                stats["balance_changes"]["increases"] += 1
            elif post_balance < pre_balance:
                stats["balance_changes"]["decreases"] += 1
            
            # If this is a builder address, add to builder's block data
            if is_mev_builder and block_number:
                # Use the current builder's address, not the first one found
                block_data = builder_blocks[address_lower][block_number]
                
                # Initialize block data if first transaction in this block
                if not block_data["block_number"]:
                    block_data["block_number"] = block_number
                    block_data["block_time"] = block_time
                
                # Add profit and balance change for this builder in this block
                block_data["total_profit_usd"] += profit_usd
                block_data["total_balance_change"] += balance_change
                
                # Track by token
                token_key = f"{currency_name} ({currency_symbol})" if currency_symbol else currency_name
                block_data["tokens"][token_key]["balance_change"] += balance_change
                block_data["tokens"][token_key]["profit_usd"] += profit_usd
        
        # Count transactions for all builder blocks that were involved in this trade
        # Track which builders we've already counted this transaction for
        builders_in_trade = set()
        for balance_join in balance_joins:
            if not isinstance(balance_join, dict):
                continue
            token_balance = balance_join.get("TokenBalance", {})
            if not token_balance or not isinstance(token_balance, dict):
                continue
            address = token_balance.get("Address", "")
            address_lower = address.lower() if address else ""
            if address_lower in mev_builder_addresses and block_number:
                if address_lower not in builders_in_trade:
                    block_data = builder_blocks[address_lower][block_number]
                    block_data["transaction_count"] += 1
                    builders_in_trade.add(address_lower)

        # Date range
        if block_time:
            if stats["date_range"]["earliest"] is None or block_time < stats["date_range"]["earliest"]:
                stats["date_range"]["earliest"] = block_time
            if stats["date_range"]["latest"] is None or block_time > stats["date_range"]["latest"]:
                stats["date_range"]["latest"] = block_time

        # Unique blocks
        if block_number:
            stats["unique_blocks"].add(block_number)

    # Convert sets to counts
    stats["unique_addresses_count"] = len(stats["unique_addresses"])
    stats["unique_blocks_count"] = len(stats["unique_blocks"])

    # Convert defaultdicts to regular dicts for JSON serialization
    # Create address summary with count and total balance change
    address_summary = []
    for address in stats["transactions_by_address"]:
        address_summary.append({
            "address": address,
            "count": stats["transactions_by_address"][address],
            "total_balance_change": stats["balance_change_by_address"][address],
        })
    address_summary.sort(key=lambda x: abs(x["total_balance_change"]), reverse=True)
    stats["address_summary"] = address_summary[:10]  # Top 10 by balance change
    
    stats["transactions_by_address"] = dict(
        sorted(stats["transactions_by_address"].items(), key=lambda x: x[1], reverse=True)[:10]
    )
    stats["transactions_by_reason"] = dict(stats["transactions_by_reason"])
    stats["dex_protocols"] = dict(sorted(stats["dex_protocols"].items(), key=lambda x: x[1], reverse=True))
    
    # Convert builder_blocks to builder summary format for template
    builder_summary = []
    for builder_address_lower, blocks_dict in builder_blocks.items():
        # Get original address for display
        display_address = mev_builder_address_map.get(builder_address_lower, builder_address_lower)
        
        # Calculate totals across all blocks for this builder
        total_profit_usd = 0.0
        total_balance_change = 0.0
        total_transactions = 0
        total_blocks = len(blocks_dict)
        all_tokens = defaultdict(lambda: {"balance_change": 0.0, "profit_usd": 0.0})
        
        # Aggregate data across all blocks
        for block_number, block_data in blocks_dict.items():
            # Aggregate tokens across all blocks
            for token_key, token_data in block_data["tokens"].items():
                all_tokens[token_key]["balance_change"] += token_data["balance_change"]
                all_tokens[token_key]["profit_usd"] += token_data["profit_usd"]
            
            total_profit_usd += block_data["total_profit_usd"]
            total_balance_change += block_data["total_balance_change"]
            total_transactions += block_data["transaction_count"]
        
        # Convert all_tokens to regular dict
        all_tokens_dict = {}
        for token_key, token_data in all_tokens.items():
            all_tokens_dict[token_key] = {
                "balance_change": token_data["balance_change"],
                "profit_usd": token_data["profit_usd"],
            }
        
        builder_summary.append({
            "address": display_address,
            "total_profit_usd": total_profit_usd,
            "total_balance_change": total_balance_change,
            "total_transactions": total_transactions,
            "total_blocks": total_blocks,
            "tokens": all_tokens_dict,
        })
    
    # Sort builders by total profit USD (descending)
    builder_summary.sort(key=lambda x: x["total_profit_usd"], reverse=True)
    stats["builder_summary"] = builder_summary

    return stats


def safe_float(value, default=0.0):
    """Safely convert a value to float, handling None, empty strings, and invalid values."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    return default


def process_builder_trades(trades, builder_address):
    """
    Transform raw trades for a specific builder into a template-friendly structure.
    """
    if not trades or not builder_address:
        return []
    
    builder_address_lower = builder_address.lower()
    processed_trades = []
    
    for trade in trades:
        if not isinstance(trade, dict):
            continue
        
        transaction = trade.get("Transaction", {}) or {}
        block = trade.get("Block", {}) or {}
        trade_info = trade.get("Trade", {}) or {}
        
        buy_info = trade_info.get("Buy", {}) or {}
        sell_info = trade_info.get("Sell", {}) or {}
        
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
        
        builder_balance_changes = []
        for balance_join in balance_joins:
            if not isinstance(balance_join, dict):
                continue
            token_balance = balance_join.get("TokenBalance", {})
            if not token_balance or not isinstance(token_balance, dict):
                continue
            token_address = token_balance.get("Address", "")
            if token_address.lower() == builder_address_lower:
                currency = token_balance.get("Currency", {}) or {}
                pre_balance = float(token_balance.get("PreBalance", 0) or 0)
                post_balance = float(token_balance.get("PostBalance", 0) or 0)
                balance_change = post_balance - pre_balance
                pre_balance_usd = float(token_balance.get("PreBalanceInUSD", 0) or 0)
                post_balance_usd = float(token_balance.get("PostBalanceInUSD", 0) or 0)
                profit_usd = post_balance_usd - pre_balance_usd
                
                builder_balance_changes.append({
                    "currency_name": currency.get("Name", "Unknown"),
                    "currency_symbol": currency.get("Symbol", ""),
                    "currency_address": currency.get("SmartContract", ""),
                    "pre_balance": pre_balance,
                    "post_balance": post_balance,
                    "balance_change": balance_change,
                    "profit_usd": profit_usd,
                    "reason_code": token_balance.get("BalanceChangeReasonCode", ""),
                })
        
        buy_currency = buy_info.get("Currency", {}) or {}
        if not isinstance(buy_currency, dict):
            buy_currency = {}
        
        sell_currency = sell_info.get("Currency", {}) or {}
        if not isinstance(sell_currency, dict):
            sell_currency = {}
        
        processed_trades.append({
            "tx_hash": transaction.get("Hash", ""),
            "block_number": block.get("Number", ""),
            "block_time": block.get("Time", ""),
            "buy": {
                "amount": safe_float(buy_info.get("Amount")),
                "amount_usd": safe_float(buy_info.get("AmountInUSD")),
                "currency_name": buy_currency.get("Name", "") if buy_currency else "",
                "currency_symbol": buy_currency.get("Symbol", "") if buy_currency else "",
                "currency_address": buy_currency.get("SmartContract", "") if buy_currency else "",
                "price": safe_float(buy_info.get("Price")),
                "price_usd": safe_float(buy_info.get("PriceInUSD")),
            },
            "sell": {
                "amount": safe_float(sell_info.get("Amount")),
                "amount_usd": safe_float(sell_info.get("AmountInUSD")),
                "currency_name": sell_currency.get("Name", "") if sell_currency else "",
                "currency_symbol": sell_currency.get("Symbol", "") if sell_currency else "",
                "currency_address": sell_currency.get("SmartContract", "") if sell_currency else "",
                "price": safe_float(sell_info.get("Price")),
                "price_usd": safe_float(sell_info.get("PriceInUSD")),
            },
            "dex_protocol": trade_info.get("Dex", {}).get("ProtocolName", "Unknown") if trade_info.get("Dex") else "Unknown",
            "balance_changes": builder_balance_changes,
        })
    
    return processed_trades

