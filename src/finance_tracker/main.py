"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .database import init_database
from .routers import categories, dashboard, imports, transactions, plaid
from .scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup: Initialize database
    await init_database()

    # Start background scheduler for Plaid sync (every 12 hours)
    # Set to 0 to disable automatic syncing
    start_scheduler(sync_interval_hours=12)

    yield

    # Shutdown: Stop scheduler
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=settings.templates_dir)

# Register routers
app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(imports.router)
app.include_router(plaid.router)
app.include_router(categories.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
