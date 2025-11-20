# MEV Relayers Profit Monitor
This is a dashboard that pulls live MEV-Boost builder income on trades executed via a private mempool from the Bitquery [MEV Balance Tracker API](https://docs.bitquery.io/docs/blockchain/Ethereum/balances/transaction-balance-tracker/eth-mev-balance-tracker/?utm_source=github&utm_medium=refferal&utm_campaign=mev_dashboard), aggregates per-builder statistics, and offers drill-down views of every trade.

## Final Output
![](/mev1.png)

### Trade-level Profit
![](/mev2.png)

## Features

- **Live data fetch + caching** – `app.py` calls Bitquery on demand, caches results for 5 minutes, and exposes `/refresh` for manual cache busting.
- **Builder summary** – `processing.calculate_stats` aggregates profit, balance deltas, blocks built, token-level PnL, protocol usage, and balance-change reason codes.
- **Builder drill-down** – `/builder/<address>` reuses the cached payload to show every trade a builder touched, with per-token balance deltas.
- **Address filtering** – `filter.py` keeps the dashboard focused on prioritized builders (set via `DEFAULT_ADDRESSES`).
- **Responsive UI** – Bootstrap-based templates (`dashboard.html`, `builder_trades.html`, `error.html`) render cleanly on desktop and mobile.

## Prerequisites

- Python 3.10+
- Bitquery Streaming/MEV Balance Tracker OAuth token

### Get a Bitquery OAuth token

You'll need a Bitquery OAuth token before the dashboard can talk to the MEV Balance Tracker API:

1. [Sign up for a free Bitquery account](https://ide.bitquery.io/?utm_source=github&utm_medium=refferal&utm_campaign=mev_dashboard)
2. [Create an access token](https://account.bitquery.io/user/api_v2/access_tokens?utm_source=github&utm_medium=refferal&utm_campaign=mev_dashboard)

Copy the generated token—you'll paste it into `config.py` in the next step.

## Installation

```bash
git clone https://github.com/Divyn/mev-boost-relay-trade-profit-monitor/tree/main
pip install -r requirements.txt
```

## Configuration

1. Create `config.py` (or edit the existing one) and add your Bitquery OAuth token:
   ```python
   TOKEN = "ey...your_bitquery_token..."
   ```
2. Optionally edit `filter.DEFAULT_ADDRESSES` to focus on a different set of builder addresses. The dashboard only shows trades that include at least one of these addresses in `joinTransactionBalances`.

## Running the dashboard

```bash
python app.py
```

Then visit `http://localhost:5000`.

- First load fetches fresh data and seeds the cache.
- `/refresh` forces a refetch (useful if you want to see the latest blocks immediately).
- `/builder/<builder_address>` surfaces the cached trades for a specific builder without hitting the API again. Visit the main dashboard at least once after starting the server so the cache is populated.

## Optional: Raw data capture

`dataservice.py` exposes `fetch_transaction_balances()` and `save_run_log()` if you want to pull the same payload outside Flask or archive the JSON response:

```bash
python dataservice.py > sample.json
```

## Project structure

```
.
├── app.py              # Flask routes + caching / builder lookup
├── config.py           # Bitquery token (never commit real secrets)
├── dataservice.py      # Bitquery client helpers
├── filter.py           # Builder allowlist + filtering helpers
├── processing.py       # Aggregation + per-builder trade shaping
├── requirements.txt    # Flask + requests
├── templates/
│   ├── dashboard.html
│   ├── builder_trades.html
│   └── error.html
└── README.md
```

## How the data flows

1. `app.py` calls `dataservice.fetch_transaction_balances()` and filters trades through `filter.filter_trades_by_addresses()`.
2. `processing.calculate_stats()` builds the dashboard-friendly summary dict.
3. `dashboard.html` renders the summary, while `builder_trades.html` uses `processing.process_builder_trades()` to show detailed trade cards.


