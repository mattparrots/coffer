"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .database import init_database
from .routers import categories, dashboard, imports, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup: Initialize database
    await init_database()
    yield
    # Shutdown: cleanup if needed


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
app.include_router(categories.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
