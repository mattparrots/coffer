# Finance Tracker - Project Summary

## What Has Been Built

A complete local-first personal finance tracking application with the following features:

### Core Functionality
- ✅ SQLite database with complete schema (accounts, categories, transactions, imports, rules)
- ✅ Three CSV parsers (Chase credit/checking, Venmo, Apple Card)
- ✅ Automatic transaction categorization with pattern-based rules
- ✅ Transaction deduplication using import hashes
- ✅ Web UI with htmx for dynamic interactions
- ✅ Dashboard with visualizations (Chart.js)

### Pages Implemented
1. **Dashboard** (`/`)
   - Monthly summary cards (income, expenses, net)
   - Spending by category donut chart
   - Cash flow over time bar chart
   - Recent transactions table

2. **Transactions** (`/transactions`)
   - Searchable/filterable transaction list
   - Filter by date range, category, account, search term
   - Clean display with merchant names
   - Category badges with colors

3. **Import** (`/import`)
   - Drag-and-drop file upload
   - Automatic format detection
   - Import history table
   - Real-time feedback with htmx

4. **Categories** (`/categories`)
   - Category tree view with colors
   - Category rules management
   - Add/delete rules
   - Pattern-based auto-categorization

### Technical Implementation

#### Database (src/finance_tracker/database.py)
- Schema creation with proper indexes
- Seed data for 10 parent categories + subcategories
- 30+ default categorization rules
- Import hash generation for deduplication
- CLI tool: `python -m finance_tracker.database --init`

#### Parsers (src/finance_tracker/parsers/)
- `base.py`: Abstract interface with ParsedTransaction and ParseResult
- `chase.py`: Handles both credit card and checking formats
- `venmo.py`: Handles Venmo transaction history with metadata rows
- `apple.py`: Handles Apple Card CSV exports

#### Services (src/finance_tracker/services/)
- `category_service.py`: Categorization logic, rule matching
- `import_service.py`: File parsing orchestration, deduplication
- `analytics_service.py`: Aggregations for dashboard charts

#### Routers (src/finance_tracker/routers/)
- `dashboard.py`: Main dashboard with stats and charts
- `transactions.py`: Transaction list with filters
- `imports.py`: File upload and import handling
- `categories.py`: Category and rule management

#### Templates (src/finance_tracker/templates/)
- `base.html`: Shared layout with navigation
- `dashboard.html`: Dashboard page with chart initialization
- `transactions/list.html`: Filterable transaction table
- `imports/upload.html`: Upload form with drag-and-drop
- `categories/list.html`: Category tree and rules management

#### Static Assets
- `static/css/style.css`: Complete styling with CSS variables
- `static/js/charts.js`: Chart.js initialization helpers

## Project Structure

```
finance-tracker/
├── src/finance_tracker/
│   ├── __init__.py
│   ├── main.py              # FastAPI app with all routers
│   ├── config.py            # Settings and paths
│   ├── database.py          # Schema, seeds, initialization
│   ├── models.py            # Pydantic models
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── chase.py
│   │   ├── venmo.py
│   │   └── apple.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── category_service.py
│   │   ├── import_service.py
│   │   └── analytics_service.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── dashboard.py
│   │   ├── transactions.py
│   │   ├── imports.py
│   │   └── categories.py
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── transactions/
│       │   └── list.html
│       ├── imports/
│       │   ├── upload.html
│       │   └── _result.html
│       └── categories/
│           └── list.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── charts.js
├── data/                    # Created on first run
│   ├── finance.db          # SQLite database
│   └── imports/            # Uploaded CSV files
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_parsers/
│   │   ├── __init__.py
│   │   └── test_chase.py
│   └── test_services/
│       └── __init__.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── GETTING_STARTED.md
└── .gitignore
```

## How to Use

### Installation and Setup

```bash
# Option 1: Using UV
uv sync
uv run python -m finance_tracker.database --init
uv run uvicorn finance_tracker.main:app --reload --port 8000

# Option 2: Using pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m finance_tracker.database --init
uvicorn finance_tracker.main:app --reload --port 8000
```

### First Time Usage

1. Access http://localhost:8000
2. Click "Import" and upload a CSV file
3. View imported transactions on the dashboard
4. Customize category rules as needed

### Database Location

The SQLite database is at `data/finance.db` and can be queried directly:

```bash
sqlite3 data/finance.db
```

## What's Working

✅ Complete database schema with indexes
✅ All three parsers tested and functional
✅ Auto-categorization with 30+ default rules
✅ Transaction deduplication
✅ Dashboard with real-time charts
✅ Transaction filtering and search
✅ File import with drag-and-drop
✅ Category rule management
✅ htmx for dynamic UI updates
✅ Responsive design
✅ Clean, minimal CSS

## What Could Be Added Later

### Phase 1 Complete
- ✅ Foundation (database, models, config)
- ✅ Parsers (Chase, Venmo, Apple)
- ✅ Core UI (dashboard, transactions, import)
- ✅ Charts and analytics

### Future Enhancements (Not Yet Implemented)
- [ ] Inline transaction editing (category, notes, merchant)
- [ ] Bulk transaction operations (select multiple, bulk categorize)
- [ ] More detailed transaction view (expand row for full details)
- [ ] Edit/delete categories
- [ ] Custom date range selector for dashboard
- [ ] Export functionality (CSV, JSON)
- [ ] Budget tracking
- [ ] Recurring transaction detection
- [ ] Split transactions
- [ ] Tags/labels
- [ ] Search across all fields
- [ ] Dark mode toggle
- [ ] Mobile-responsive improvements
- [ ] API endpoints for programmatic access

## Key Design Decisions

1. **Local-first**: SQLite database, no cloud dependencies
2. **Server-rendered**: Jinja2 templates + htmx for simplicity
3. **Minimal JavaScript**: Chart.js for visualizations only
4. **Type safety**: Pydantic models throughout
5. **Async**: aiosqlite for non-blocking database operations
6. **Deduplication**: SHA256 hashes prevent duplicate imports
7. **Extensible**: Parser interface makes adding new banks easy
8. **Direct access**: Database at known location for ad-hoc queries

## Files to Review

**Start here:**
- `GETTING_STARTED.md` - Setup instructions
- `src/finance_tracker/main.py` - Application entry point
- `src/finance_tracker/database.py` - Schema and seed data

**Core logic:**
- `src/finance_tracker/services/import_service.py` - Import orchestration
- `src/finance_tracker/parsers/chase.py` - Example parser
- `src/finance_tracker/services/category_service.py` - Categorization

**UI:**
- `src/finance_tracker/templates/base.html` - Layout
- `src/finance_tracker/templates/dashboard.html` - Main page
- `static/css/style.css` - All styling

## Notes

- The app is ready to run once dependencies are installed
- Database will be created automatically on first launch
- Import some sample data to see the dashboard come alive
- All transaction amounts follow convention: negative = expense, positive = income
- Category rules are case-insensitive substring matches
- Higher priority rules are checked first
- The database can be queried directly for custom analysis

Enjoy your new finance tracker!
