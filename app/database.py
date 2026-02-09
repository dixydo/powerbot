from typing import List, Optional
import logging
import psycopg
import pytz
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from config import Config

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[AsyncConnectionPool] = None

def get_connection_info() -> str:
    return f"host={Config.DB_HOST} port={Config.DB_PORT} dbname={Config.DB_NAME} user={Config.DB_USER} password={Config.DB_PASSWORD}"

async def init_db_pool():
    """Initialize database connection pool"""
    global _pool
    if _pool is None:
        connection_info = get_connection_info()
        _pool = AsyncConnectionPool(
            conninfo=connection_info,
            min_size=2,
            max_size=10,
            timeout=30,
            max_idle=300,
            max_lifetime=3600,
        )
        await _pool.open()
        logger.info("Database connection pool initialized")

async def close_db_pool():
    """Close database connection pool"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")

def get_pool() -> AsyncConnectionPool:
    """Get the database connection pool"""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    return _pool

async def add_user(user_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None):
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO users (telegram_user_id, username, first_name, last_name, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (telegram_user_id) DO UPDATE SET 
                    is_active = TRUE,
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    updated_at = NOW()
                """,
                (user_id, username, first_name, last_name)
            )
            await conn.commit()

async def get_active_users() -> List[int]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT telegram_user_id FROM users WHERE is_active = TRUE")
            rows = await cur.fetchall()
            return [row[0] for row in rows]

async def log_power_event(status: str, timestamp: float):
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            from datetime import datetime
            import pytz
            kiev_tz = pytz.timezone(Config.TIMEZONE)
            created_at = datetime.fromtimestamp(timestamp, tz=kiev_tz)
            await cur.execute(
                "INSERT INTO power_events (state, created_at) VALUES (%s, %s)",
                (status, created_at)
            )
            await conn.commit()

async def get_last_event() -> Optional[dict]:
    pool = get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT state, created_at FROM power_events ORDER BY id DESC LIMIT 1"
                )
                row = await cur.fetchone()
                if row:
                    result = dict(row)
                    # Convert to UTC timestamp for consistent comparison
                    created_at_utc = result['created_at'].astimezone(pytz.UTC)
                    return {
                        'status': result['state'],
                        'timestamp': created_at_utc.timestamp()
                    }
                return None
    except Exception as e:
        logger.exception(f"Error in get_last_event: {e}")
        raise

async def get_power_events(limit: int = 100) -> List[dict]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT state, created_at FROM power_events ORDER BY id DESC LIMIT %s",
                (limit,)
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def deactivate_user(user_id: int):
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET is_active = FALSE WHERE telegram_user_id = %s",
                (user_id,)
            )
            await conn.commit()

async def log_activity(action: str, user_id: int = None, details: str = None, recipients_count: int = 0):
    """Log bot activity"""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO activity_logs (action, user_id, details, recipients_count)
                VALUES (%s, %s, %s, %s)
                """,
                (action, user_id, details, recipients_count)
            )
            await conn.commit()
