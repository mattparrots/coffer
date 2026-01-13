"""Background job scheduler for automatic transaction syncing."""

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .database import get_db
from .services.sync_service import sync_all_active_items

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def sync_job():
    """
    Background job to sync all active Plaid items.

    This runs periodically to fetch new transactions from connected banks.
    """
    logger.info("Starting scheduled sync job...")
    try:
        async with get_db() as db:
            results = await sync_all_active_items(db)

        logger.info(
            f"Scheduled sync complete: "
            f"{results['items_synced']} items, "
            f"+{results['total_added']} transactions, "
            f"~{results['total_updated']} updated, "
            f"-{results['total_removed']} removed"
        )

        if results['errors']:
            logger.warning(f"Sync errors: {results['errors']}")

    except Exception as e:
        logger.error(f"Error in scheduled sync job: {e}", exc_info=True)


def start_scheduler(sync_interval_hours: int = 12):
    """
    Start the background scheduler.

    Args:
        sync_interval_hours: How often to sync (default: 12 hours)
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    logger.info(f"Starting scheduler with {sync_interval_hours}h sync interval...")

    _scheduler = AsyncIOScheduler()

    # Add sync job
    _scheduler.add_job(
        sync_job,
        trigger=IntervalTrigger(hours=sync_interval_hours),
        id="plaid_sync",
        name="Sync Plaid transactions",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    _scheduler.start()
    logger.info("Scheduler started successfully")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler

    if _scheduler is not None:
        logger.info("Stopping scheduler...")
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Scheduler stopped")


def get_scheduler() -> AsyncIOScheduler | None:
    """Get the scheduler instance."""
    return _scheduler


async def trigger_immediate_sync():
    """
    Trigger an immediate sync outside of the scheduled interval.

    Useful for manual "Sync Now" buttons in the UI.
    """
    logger.info("Triggering immediate sync...")
    await sync_job()
