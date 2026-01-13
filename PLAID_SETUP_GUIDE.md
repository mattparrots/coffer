# Plaid Integration Setup Guide

Your Finance Tracker now has full Plaid integration built! Here's how to get it running.

## 🎉 What's Been Built

✅ **Backend Services**
- Plaid API client with link token generation, token exchange, and transaction sync
- Encryption utility for securing access tokens
- Background scheduler for automatic transaction syncing (every 12 hours)
- Complete database schema with new tables for Plaid items and accounts

✅ **API Endpoints**
- `/plaid/link/token` - Create link token for Plaid Link
- `/plaid/link/exchange` - Exchange public token after connection
- `/plaid/connections` - Manage connected banks (page)
- `/plaid/sync` - Manual sync all accounts
- `/plaid/webhook` - Webhook handler for Plaid events
- Plus more for individual item management

✅ **Frontend**
- "Bank Connections" page with Plaid Link integration
- Connection status on dashboard
- Transaction source badges (CSV vs Plaid)
- Sync buttons and status indicators

---

## 📋 Prerequisites

Before you start, you'll need:

1. **Plaid Developer Account** (free)
   - Sign up at: https://dashboard.plaid.com/signup
   - No credit card required for sandbox/development

2. **Python Dependencies**
   - Already added to `requirements.txt`
   - You'll need to install them (see steps below)

---

## 🚀 Setup Steps

### Step 1: Create Plaid Account

1. Go to https://dashboard.plaid.com/signup
2. Sign up for a free account
3. Complete the onboarding flow
4. You'll start in **Sandbox** mode (test data only)

### Step 2: Get Your Plaid Credentials

1. In the Plaid Dashboard, go to **Keys** section
2. Copy these values:
   - **Client ID**: `your_client_id`
   - **Sandbox Secret**: `your_sandbox_secret`
   - **Environment**: `sandbox` (to start)

### Step 3: Generate Encryption Key

This encrypts your Plaid access tokens in the database.

Run this command to generate a key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output (looks like: `A1B2C3D4E5F6...`)

### Step 4: Create `.env` File

Create a file called `.env` in the project root (`/home/user/coffer/.env`):

```env
# Plaid Configuration
FINANCE_TRACKER_PLAID_CLIENT_ID=your_client_id_here
FINANCE_TRACKER_PLAID_SECRET=your_sandbox_secret_here
FINANCE_TRACKER_PLAID_ENV=sandbox

# Encryption Key (from Step 3)
FINANCE_TRACKER_ENCRYPTION_KEY=your_encryption_key_here
```

**Replace the placeholders with your actual values!**

### Step 5: Install Dependencies

```bash
# If using uv (recommended):
uv sync

# Or if using pip:
pip install -r requirements.txt
```

### Step 6: Reinitialize Database

The database schema has been updated with new Plaid tables. Run:

```bash
# Using uv:
uv run python -m finance_tracker.database --init

# Or with pip:
python -m finance_tracker.database --init
```

This will add the new tables:
- `plaid_items` - Connected bank items
- `plaid_accounts` - Individual accounts per item
- Updated `accounts` table with `source` field
- Updated `transactions` table with `plaid_transaction_id` and `is_pending`

### Step 7: Start the Application

```bash
# Using uv:
uv run uvicorn finance_tracker.main:app --reload --port 8000

# Or with pip:
uvicorn finance_tracker.main:app --reload --port 8000
```

Visit: http://localhost:8000

---

## 🏦 Connecting Your First Bank (Sandbox)

### Using Sandbox Test Banks

1. Open http://localhost:8000
2. Click **"Bank Connections"** in the sidebar
3. Click **"Connect Bank Account"**
4. In the Plaid Link modal:
   - Search for: **"First Platypus Bank"** (Plaid's test bank)
   - Username: `user_good`
   - Password: `pass_good`
5. Select which accounts to connect
6. Click **Continue**

The app will:
- Exchange the token for an access token
- Create account records
- Sync last 30 days of transactions (test data)
- Redirect to dashboard

### Test Credentials for Sandbox

Plaid provides these test credentials:

| Scenario | Username | Password | Result |
|----------|----------|----------|--------|
| Success | `user_good` | `pass_good` | Works perfectly |
| Invalid credentials | `user_bad` | `pass_bad` | Simulates login failure |

---

## 📊 How It Works

### Automatic Syncing

- **Background job runs every 12 hours**
- Fetches new/updated/removed transactions
- Auto-categorizes using your existing rules
- Updates balances

### Manual Syncing

- Click "Sync Now" on Bank Connections page
- Or sync individual banks

### Transaction Deduplication

- Plaid transactions are tracked by `plaid_transaction_id` (unique)
- CSV imports use `import_hash` (existing system)
- No duplicates between sources

### Account Source Tracking

- Each transaction shows a badge: 🔗 Plaid or 📁 CSV
- Keeps CSV import as fallback option
- Both sources work side-by-side

---

## 🔐 Security

### Access Token Encryption

- All Plaid access tokens are encrypted using Fernet (AES-128)
- Stored encrypted in database
- Decrypted only when needed for API calls

### Environment Variables

- All sensitive data in `.env` file
- `.env` is gitignored (won't be committed)
- Never commit secrets to git

### Webhook Validation

- Plaid webhooks are received at `/plaid/webhook`
- In production, you should validate webhook signatures
- For personal use, this is less critical

---

## 🎯 Moving from Sandbox → Development → Production

### Development Environment

Once you're ready to connect real banks:

1. In Plaid Dashboard, request **Development** access
2. Update `.env`:
   ```env
   FINANCE_TRACKER_PLAID_ENV=development
   FINANCE_TRACKER_PLAID_SECRET=your_development_secret
   ```
3. Restart the app

**Development tier is FREE for up to 100 connected accounts** - perfect for personal use!

### Production Environment

For production (real money, real transactions):

1. Complete Plaid's production application process
2. Update to production credentials
3. Set up webhooks in Plaid Dashboard
4. Use HTTPS (Plaid requirement)

**Note:** For personal use, Development tier is likely all you need!

---

## 📁 File Structure (New Files)

```
src/finance_tracker/
├── encryption.py               # Token encryption utility
├── scheduler.py                # Background sync scheduler
├── services/
│   ├── plaid_service.py       # Plaid API client
│   └── sync_service.py        # Transaction sync logic
├── routers/
│   └── plaid.py               # API endpoints
└── templates/
    └── plaid/
        └── connections.html    # Bank connections page
```

---

## 🛠️ Configuration Options

### Sync Frequency

Edit `main.py` line 23 to change sync interval:

```python
start_scheduler(sync_interval_hours=12)  # Change to 6, 24, etc.
```

Set to `0` to disable automatic syncing:

```python
start_scheduler(sync_interval_hours=0)  # Manual sync only
```

### Pending Transactions

Currently, pending transactions are **skipped** (see `sync_service.py` line 127).

To include pending transactions:
1. Edit `sync_service.py`
2. Comment out the pending check
3. They'll show with a source badge

---

## 🐛 Troubleshooting

### "Encryption key not configured"

**Problem:** App crashes on startup with encryption error.

**Solution:** Make sure `.env` file has `FINANCE_TRACKER_ENCRYPTION_KEY` set.

### "Failed to create link token"

**Problem:** Plaid Link doesn't open.

**Solutions:**
- Check `FINANCE_TRACKER_PLAID_CLIENT_ID` in `.env`
- Check `FINANCE_TRACKER_PLAID_SECRET` in `.env`
- Make sure you're using the **Sandbox** secret (not Development or Production)

### "Failed to exchange token"

**Problem:** Connection succeeds in Plaid Link but fails afterward.

**Solutions:**
- Check browser console for errors
- Verify database was reinitialized with new schema
- Check server logs for detailed error message

### "No transactions synced"

**Problem:** Bank connects but no transactions appear.

**Solutions:**
- Sandbox accounts have limited test data
- Check "Bank Connections" page to see sync status
- Click "Sync" button to manually trigger
- Check server logs for sync errors

### Database Schema Issues

**Problem:** Errors about missing columns/tables.

**Solution:** Drop the old database and reinitialize:

```bash
rm data/finance.db
uv run python -m finance_tracker.database --init
```

⚠️ **Warning:** This deletes all existing data!

---

## 📝 Next Steps

### Immediate

1. ✅ Create Plaid account
2. ✅ Get credentials
3. ✅ Generate encryption key
4. ✅ Create `.env` file
5. ✅ Install dependencies
6. ✅ Reinitialize database
7. ✅ Start app
8. ✅ Connect test bank

### Future Enhancements

Ideas for extending this:

- **Balance tracking**: Display current balances on dashboard
- **Multi-user**: Add authentication for multiple users
- **Mobile app**: Build React Native app using the same API
- **Notifications**: Email alerts for large transactions
- **Budgeting**: Set category budgets with alerts
- **Webhooks**: Set up Plaid webhooks in dashboard for instant updates

---

## 📚 Resources

- **Plaid Documentation**: https://plaid.com/docs/
- **Plaid Dashboard**: https://dashboard.plaid.com/
- **Plaid API Reference**: https://plaid.com/docs/api/
- **Support**: https://plaid.com/docs/support/

---

## 🎉 You're Ready!

Your finance tracker now has:
- ✅ Automatic bank syncing
- ✅ Secure token encryption
- ✅ Background job scheduler
- ✅ Beautiful UI with connection management
- ✅ Transaction source tracking

All while keeping CSV imports as a fallback option!

Enjoy your automated finance tracking! 🚀
