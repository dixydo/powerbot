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

from bot import start_bot, bot
from monitor import monitor_loop

logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Starting Power Bot...")
    
    bot_task = asyncio.create_task(start_bot())
    monitor_task = asyncio.create_task(monitor_loop(bot))
    
    await asyncio.gather(bot_task, monitor_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
