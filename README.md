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
- **Intervention Feed** — Fin-R1-powered saving recommendations
- **Transaction Explorer** — Full searchable transaction table

## Setup

```bash
pip install -r requirements.txt
```

Set your Hugging Face token:
```bash
export HF_TOKEN=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
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

## Gmail Integration (Optional)

Import transactions directly from bank email alerts.

### Setup Gmail API

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project

2. **Enable Gmail API:**
   - In your project, enable the Gmail API
   - Go to "Credentials" → "Create Credentials"
   - Select "OAuth 2.0 Desktop Application"
   - Download the credentials JSON

3. **Configure SpendLens:**
   - Place the downloaded `credentials.json` in the project root directory
   - First run will prompt you to authorize Gmail access

4. **Import Transactions:**
   - Navigate to `/email_import` page
   - Click "Fetch Available Banks" to scan your inbox
   - Select banks to import from
   - Click "Import Selected Banks"
   - Transactions will be automatically extracted and imported

The app uses Fin-R1 (via Hugging Face) to intelligently extract:
- Transaction date and time
- Amount
- Merchant name
- Transaction type (debit/credit/investment)
- Description

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
