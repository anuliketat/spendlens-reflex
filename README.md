# SpendLens

A personal finance dashboard built with [Reflex](https://reflex.dev) (Python).

## Features

- **Command Header** — AI-generated verdict on your spending posture
- **Live Feed Strip** — Real-time transaction stream with flagging
- **Weekly Pulse** — Budget burn rate vs. time elapsed
- **Monthly Battlefield** — Category-by-category budget vs. actual
- **Merchant Lens** — Top merchants with annual spend projection
- **Two-Tier Spend Map** — Routine vs. one-off spend separation
- **Spending Archetype** — AI-generated persona based on your habits
- **Quarterly Drift** — Month-over-month category shift detection
- **Intervention Feed** — Gemini-powered saving recommendations
- **Transaction Explorer** — Full searchable transaction table

## Setup

```bash
pip install -r requirements.txt
```

Set your Gemini API key:
```bash
export GEMINI_API_KEY=your_key_here
```

Initialize the database:
```bash
reflex db makemigrations
reflex db migrate
```

Run the app:
```bash
reflex run
```

## CSV Format

Ingest transactions from a CSV file with these columns:

| Column     | Format                    |
|------------|---------------------------|
| datetime   | ISO 8601 (e.g. 2025-01-15 14:30:00) |
| amount     | float (e.g. 349.00)       |
| merchant   | string (e.g. Swiggy)      |
| category   | string (e.g. food)        |
| txn_type   | string (e.g. debit)       |

## Webhook

POST live transactions to `/api/transaction`:

```json
{
  "datetime": "2025-01-15T14:30:00",
  "amount": 349.0,
  "merchant": "Swiggy",
  "category": "food",
  "txn_type": "debit"
}
```
