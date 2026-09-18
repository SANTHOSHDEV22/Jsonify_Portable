# Jsonify License Server

FastAPI backend for Jsonify Pro purchases, Azure SQL persistence, signed
lifetime licenses, Razorpay payment-link webhooks and SMTP delivery.

## Requirements

- Python 3.11+
- Microsoft ODBC Driver 18 for SQL Server
- Azure SQL Database
- Razorpay account
- SMTP provider
- RSA private/public key pair

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and enter your test credentials.

## RSA keys

Generate a private key locally:

```bash
openssl genpkey -algorithm RSA -out secrets/license_private.pem -pkeyopt rsa_keygen_bits:3072
```

Generate the matching public key:

```bash
openssl rsa -pubout -in secrets/license_private.pem -out license_public.pem
```

Never commit the private key. Copy only `license_public.pem` into the Jsonify
desktop application's resources.

## Azure SQL

Create an Azure SQL database named `jsonify_license` (or update `.env`).

The application currently calls SQLAlchemy `create_all()` on startup to
bootstrap tables. For mature production deployments, use Alembic migrations
instead of relying on `create_all()`.

Azure SQL must allow the deployed backend to connect. Prefer managed identity
or Azure Key Vault for production secrets where possible.

## Run

```powershell
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Razorpay webhook

Configure the provider webhook endpoint as:

`https://YOUR-LICENSE-DOMAIN/v1/webhooks/razorpay`

Subscribe to the successful payment-link event used by this service.

## Database tables

The service persists:

- customers
- orders
- payments
- licenses
- webhook_events
- email_deliveries

Unique constraints on order IDs, payment IDs, license IDs and webhook event
identity provide the foundation for idempotent payment processing.

## Production notes

Do not store production secrets in `.env` committed to Git. Use the hosting
platform's secret store / Azure Key Vault.

Do not ship `license_private.pem` with the Jsonify desktop application.

Test the entire flow with Razorpay test credentials before switching to live
credentials.
