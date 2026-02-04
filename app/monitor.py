import asyncio
import time
import logging
import random
from tapo import ApiClient
from config import Config
from database import log_power_event, get_last_event

logger = logging.getLogger(__name__)

async def check_plug_status() -> bool:
    if Config.TEST_MODE:
        # Test mode: simulate random power state changes
        return random.choice([True, False])
    
    max_retries = 3
    
    for attempt in range(max_retries):
        client = None
        try:
            client = ApiClient(Config.TAPO_EMAIL, Config.TAPO_PASSWORD)
            device = await asyncio.wait_for(client.p100(Config.DEVICE_IP), timeout=5.0)
            await asyncio.wait_for(device.get_device_info(), timeout=5.0)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Timeout connecting to device (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            continue
        except Exception as e:
            logger.warning(f"Error checking device (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            continue
        finally:
            if client:
                try:
                    await client.close()
                except:
                    pass  # Ignore errors during cleanup
    
    logger.error("Failed to connect to device after all retries")
    return False

def format_duration(seconds: float) -> str:
    hours, rem = divmod(int(seconds), 3600)
    minutes, _ = divmod(rem, 60)
    return f"{hours}h {minutes}m"

async def monitor_loop(bot):
    if Config.TEST_MODE:
        logger.info("🚀 Monitoring started in TEST MODE (simulating power changes)")
    else:
        logger.info(f"🚀 Monitoring started on {Config.DEVICE_IP}")
    
    pending_state: str | None = None
    pending_count: int = 0
    pending_first_time: float | None = None
    
    while True:
        try:
            current_state = await check_plug_status()
            current_status_str = "on" if current_state else "off"
            logger.info(f"Current state: {current_status_str}")
            
            last_event = await get_last_event()
            
            if not last_event:
                now = time.time()
                await log_power_event(current_status_str, now)
                logger.info(f"First event recorded: {current_status_str}")
                pending_state = None
                pending_count = 0
            else:
                last_state_str = last_event.get('status')
                last_time = last_event.get('timestamp')
                
                if current_status_str != last_state_str:
                    if pending_state == current_status_str:
                        pending_count += 1
                        logger.info(f"State change pending: {last_state_str} -> {current_status_str} (confirmation {pending_count}/{Config.CONFIRMATION_CHECKS})")
                    else:
                        pending_state = current_status_str
                        pending_count = 1
                        pending_first_time = time.time()
                        logger.info(f"State change detected: {last_state_str} -> {current_status_str} (confirmation 1/{Config.CONFIRMATION_CHECKS})")
                    
                    if pending_count >= Config.CONFIRMATION_CHECKS:
                        now = pending_first_time if pending_first_time else time.time()
                        duration = now - last_time
                        time_str = format_duration(duration)
                        
                        if current_state:
                            msg = f"✅ **Світло З'ЯВИЛОСЯ!**\n\n🌑 Світло було вимкнено: `{time_str}`"
                        else:
                            msg = f"❌ **Світло ЗНИКЛО!**\n\n💡 Було доступне: `{time_str}`"
                        
                        logger.info(f"State change confirmed: {last_state_str} -> {current_status_str}")
                        
                        await log_power_event(current_status_str, now)
                        
                        from bot import broadcast_message
                        await broadcast_message(bot, msg)
                        
                        pending_state = None
                        pending_count = 0
                        pending_first_time = None
                else:
                    if pending_state is not None:
                        logger.info(f"State change cancelled: was pending {pending_state}, but current is {current_status_str}")
                        pending_state = None
                        pending_count = 0
                        pending_first_time = None
        
        except asyncio.CancelledError:
            logger.info("Monitoring stopped")
            raise
        except Exception as e:
            logger.exception(f"Error in monitoring loop: {e}")
        
        if Config.TEST_MODE:
            # In test mode, use random interval between 2-3 minutes
            sleep_time = random.randint(120, 180)
            logger.info(f"Test mode: next check in {sleep_time//60}m {sleep_time%60}s")
            await asyncio.sleep(sleep_time)
        else:
            await asyncio.sleep(Config.CHECK_INTERVAL)
        
        
