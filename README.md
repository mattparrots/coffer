# Finance Tracker

A local-first personal finance app for importing, categorizing, and visualizing financial data.

## Features

- Import transactions from CSV files (Chase, Venmo, Apple Card)
- Automatic categorization with customizable rules
- Interactive dashboard with spending visualizations
- Transaction management and filtering
- SQLite database for easy querying

## Quick Start

```bash
# Install dependencies
uv sync

# Initialize database
uv run python -m finance_tracker.database --init

# Run development server
uv run uvicorn finance_tracker.main:app --reload --port 8000
```

Access the app at http://localhost:8000

## Project Structure

- `src/finance_tracker/` - Main application code
- `data/` - SQLite database and import files
- `static/` - CSS and JavaScript assets
- `tests/` - Test suite

## Database

The SQLite database is located at `data/finance.db`. You can query it directly with:

```bash
sqlite3 data/finance.db
```

## Supported Import Formats

- Chase Credit Card CSV
- Chase Checking CSV
- Venmo Transaction History CSV
- Apple Card CSV
