# Getting Started with Finance Tracker

This guide will help you set up and run the Finance Tracker application.

## Prerequisites

- Python 3.12 or higher
- UV package manager (recommended) or pip

## Installation

### Option 1: Using UV (Recommended)

```bash
# Install dependencies
uv sync

# Initialize the database
uv run python -m finance_tracker.database --init

# Run the application
uv run uvicorn finance_tracker.main:app --reload --port 8000
```

### Option 2: Using pip and venv

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize the database
python -m finance_tracker.database --init

# Run the application
uvicorn finance_tracker.main:app --reload --port 8000
```

## First Steps

1. **Access the application**: Open your browser to http://localhost:8000

2. **Import your first transactions**:
   - Click "Import" in the sidebar
   - Upload a CSV file from Chase, Venmo, or Apple Card
   - The app will automatically detect the format and import transactions

3. **View your dashboard**:
   - See income, expenses, and cash flow visualizations
   - Browse recent transactions
   - Explore spending by category

4. **Manage transactions**:
   - Click "Transactions" to see all imported data
   - Use filters to search and narrow down results
   - Transactions are automatically categorized based on rules

5. **Customize categories**:
   - Click "Categories" to see all available categories
   - Add new category rules to improve auto-categorization
   - Rules match patterns in transaction descriptions (case-insensitive)

## Database Location

The SQLite database is located at: `data/finance.db`

You can query it directly with:
```bash
sqlite3 data/finance.db
```

Example queries:
```sql
-- See all transactions
SELECT date, description, amount, category_id FROM transactions ORDER BY date DESC LIMIT 10;

-- Total spending by month
SELECT strftime('%Y-%m', date) as month, SUM(ABS(amount)) as total
FROM transactions
WHERE amount < 0
GROUP BY month
ORDER BY month DESC;

-- Top merchants
SELECT merchant, COUNT(*) as count, SUM(ABS(amount)) as total
FROM transactions
WHERE amount < 0 AND merchant IS NOT NULL
GROUP BY merchant
ORDER BY total DESC
LIMIT 10;
```

## Supported Import Formats

### Chase Credit Card CSV
Expected columns:
- Transaction Date
- Post Date
- Description
- Category
- Type
- Amount

### Chase Checking CSV
Expected columns:
- Details
- Posting Date
- Description
- Amount
- Type
- Balance

### Venmo CSV
Expected columns:
- Datetime
- Type
- Status
- Note
- From
- To
- Amount (total)

### Apple Card CSV
Expected columns:
- Transaction Date
- Clearing Date
- Description
- Merchant
- Category
- Type
- Amount (USD)

## Project Structure

```
finance-tracker/
├── src/finance_tracker/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── database.py          # Database schema and initialization
│   ├── models.py            # Pydantic models
│   ├── parsers/             # CSV parsers
│   ├── services/            # Business logic
│   ├── routers/             # API routes
│   └── templates/           # HTML templates
├── static/                  # CSS and JavaScript
├── data/                    # Database and imports
└── tests/                   # Test suite
```

## Next Steps

- Add more category rules to improve auto-categorization
- Import historical data from multiple accounts
- Explore the dashboard charts to understand spending patterns
- Query the database directly for custom analysis

## Troubleshooting

**Import fails**: Check that your CSV file matches one of the supported formats. The first row should contain headers.

**Database not found**: Run `python -m finance_tracker.database --init` to create it.

**Port 8000 already in use**: Use a different port: `uvicorn finance_tracker.main:app --reload --port 8001`

**Module not found**: Make sure you're in the project root directory and dependencies are installed.
