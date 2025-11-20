import json
import os
import config
import requests

BITQUERY_URL = "https://streaming.bitquery.io/graphql"


def _build_query(limit: int) -> str:
    return f"""{{
  EVM(dataset: realtime, network: eth) {{
    DEXTrades(limit: {{count: {limit}}}, where: {{Fee: {{PriorityFeePerGas: {{eq: "0"}}}}}}) {{
      Block {{
        Time
        Number
      }}
      Fee {{
        Burnt
        BurntInUSD
        EffectiveGasPrice
        EffectiveGasPriceInUSD
        GasRefund
        MinerReward
        MinerRewardInUSD
        PriorityFeePerGas
        PriorityFeePerGasInUSD
        Savings
        SavingsInUSD
        SenderFee
        SenderFeeInUSD
      }}
      Receipt {{
        ContractAddress
        Status
      }}
      TransactionStatus {{
        Success
      }}
      Log {{
        Signature {{
          Name
        }}
        SmartContract
      }}
      Call {{
        From
        InternalCalls
        Signature {{
          Name
          Signature
        }}
        To
        Value
      }}
      Transaction {{
        Gas
        Cost
        CostInUSD
        GasFeeCap
        GasFeeCapInUSD
        GasPrice
        GasPriceInUSD
        GasTipCap
        GasTipCapInUSD
        Index
        Nonce
        Protected
        Time
        Type
        Value
        ValueInUSD
        Hash
        From
        To
      }}
      Trade {{
        Buy {{
          Amount
          AmountInUSD
          Buyer
          Seller
          Currency {{
            Decimals
            Name
            Symbol
            SmartContract
          }}
          Price
          PriceInUSD
        }}
        Sell {{
          Amount
          AmountInUSD
          Buyer
          Seller
          Currency {{
            Name
            Symbol
            SmartContract
          }}
          Price
          PriceInUSD
        }}
        Dex {{
          ProtocolName
          SmartContract
          OwnerAddress
        }}
      }}
      joinTransactionBalances(Transaction_Hash: Transaction_Hash, join: inner) {{
        TokenBalance {{
          Address
          BalanceChangeReasonCode
          Currency {{
            Name
            Symbol
            SmartContract
          }}
          PostBalance
          PostBalanceInUSD
          PreBalance
          PreBalanceInUSD
        }}
        Transaction {{
          Hash
        }}
      }}
    }}
  }}
}}"""


def fetch_transaction_balances(limit: int = 20000) -> dict:
    """
    Fetch the latest DEXTrades from the Bitquery streaming API.

    Returns the decoded JSON payload as a Python dictionary.
    """
    query = _build_query(limit)
    payload = json.dumps({"query": query, "variables": "{}"})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.TOKEN}",
    }

    response = requests.post(BITQUERY_URL, headers=headers, data=payload, timeout=60)
    response.raise_for_status()
    
    data = response.json()
    
    # Validate response structure
    if not isinstance(data, dict):
        print(f"Unexpected response type: {type(data)}")
        return {"data": {"EVM": {"DEXTrades": []}}}
    
    if "data" not in data:
        print("Response missing 'data' key")
        return {"data": {"EVM": {"DEXTrades": []}}}
    
    if not isinstance(data["data"], dict):
        print(f"Response 'data' is not a dict: {type(data['data'])}")
        return {"data": {"EVM": {"DEXTrades": []}}}
    
    if "EVM" not in data["data"]:
        print("Response missing 'EVM' key")
        return {"data": {"EVM": {"DEXTrades": []}}}
    
    if not isinstance(data["data"]["EVM"], dict):
        print(f"Response 'EVM' is not a dict: {type(data['data']['EVM'])}")
        return {"data": {"EVM": {"DEXTrades": []}}}
    
    # Ensure DEXTrades exists and is a list
    if "DEXTrades" not in data["data"]["EVM"]:
        data["data"]["EVM"]["DEXTrades"] = []
    elif not isinstance(data["data"]["EVM"]["DEXTrades"], list):
        data["data"]["EVM"]["DEXTrades"] = []
    
    return data


def save_run_log(data: dict, path: str = "run.log") -> None:
    """Persist the supplied response dict to disk."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    payload = fetch_transaction_balances()
    print(json.dumps(payload, indent=2))