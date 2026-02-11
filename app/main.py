#!/usr/bin/env python3
"""
Power Bot - Main Application
"""
import asyncio
import logging
import sys
import warnings
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Hide pydantic warnings about protected namespaces
warnings.filterwarnings("ignore", message=".*protected namespace.*")

from config import Config
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def sentry_before_send(event, hint):
    """Filter out expected errors from Sentry"""
    # Ignore TelegramForbiddenError - user blocked the bot
    if 'exc_info' in hint and hint['exc_info'][0].__name__ == 'TelegramForbiddenError':
        return None

    # Ignore log messages about Tapo device connection failures (expected when power is off)
    if 'log_record' in hint:
        message = hint['log_record'].getMessage()
        if 'Failed to connect to device' in message or 'Timeout connecting to device' in message:
            return None

    return event


# Initialize Sentry
if Config.SENTRY_DSN:
    sentry_sdk.init(
        dsn=Config.SENTRY_DSN,
        environment=Config.SENTRY_ENVIRONMENT,
        traces_sample_rate=Config.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            AsyncioIntegration(),
            LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors and above as events
            ),
        ],
        before_send=sentry_before_send,
    )
    logging.info("Sentry initialized")

from bot import start_bot, bot
from monitor import monitor_loop
from database import init_db_pool, close_db_pool

logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Starting Power Bot...")

    # Initialize database connection pool
    await init_db_pool()

    try:
        bot_task = asyncio.create_task(start_bot())
        monitor_task = asyncio.create_task(monitor_loop(bot))
        
        # Wait for tasks with proper error handling
        done, pending = await asyncio.wait(
            [bot_task, monitor_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        # Check if any task failed
        for task in done:
            if task.exception():
                logger.error(f"Task failed: {task.exception()}")
                raise task.exception()
                
    except asyncio.CancelledError:
        logger.info("🛑 Bot stopped")
        raise
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # Always close the database connection pool
        await close_db_pool()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
