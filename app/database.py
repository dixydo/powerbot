from typing import List, Optional
import logging
import psycopg
from psycopg.rows import dict_row
from config import Config

logger = logging.getLogger(__name__)

def get_connection_info() -> str:
    return f"host={Config.DB_HOST} port={Config.DB_PORT} dbname={Config.DB_NAME} user={Config.DB_USER} password={Config.DB_PASSWORD}"

async def add_user(user_id: int, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None):
    connection_info = get_connection_info()
    async with await psycopg.AsyncConnection.connect(connection_info) as conn:
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
    connection_info = get_connection_info()
    async with await psycopg.AsyncConnection.connect(connection_info) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT telegram_user_id FROM users WHERE is_active = TRUE")
            rows = await cur.fetchall()
            return [row[0] for row in rows]

async def log_power_event(status: str, timestamp: float):
    connection_info = get_connection_info()
    async with await psycopg.AsyncConnection.connect(connection_info) as conn:
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
    connection_info = get_connection_info()
    try:
        async with await psycopg.AsyncConnection.connect(connection_info, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT state, created_at FROM power_events ORDER BY id DESC LIMIT 1"
                )
                row = await cur.fetchone()
                if row:
                    result = dict(row)
                    return {
                        'status': result['state'],
                        'timestamp': result['created_at'].timestamp()
                    }
                return None
    except Exception as e:
        logger.exception(f"Error in get_last_event: {e}")
        raise

async def get_power_events(limit: int = 100) -> List[dict]:
    connection_info = get_connection_info()
    async with await psycopg.AsyncConnection.connect(connection_info, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT state, created_at FROM power_events ORDER BY id DESC LIMIT %s",
                (limit,)
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def deactivate_user(user_id: int):
    connection_info = get_connection_info()
    async with await psycopg.AsyncConnection.connect(connection_info) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET is_active = FALSE WHERE telegram_user_id = %s",
                (user_id,)
            )
            await conn.commit()

async def log_notification(user_id: int, message: str, status: str):
    # Log notification via migrations-managed `notifications` table.
    # The table should be created by migration `003_create_notifications.sql`.
    connection_info = get_connection_info()
    async with await psycopg.AsyncConnection.connect(connection_info) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO notifications (telegram_user_id, message, status) VALUES (%s, %s, %s)",
                (user_id, message, status)
            )
            await conn.commit()
