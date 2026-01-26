import logging
import time
from datetime import datetime

import pytz
from aiogram import Bot, Dispatcher, F, types
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command
from aiogram.enums import ParseMode
from config import Config
from database import add_user, get_active_users, deactivate_user, log_notification, get_last_event, get_power_events
from monitor import check_plug_status

logger = logging.getLogger(__name__)

def format_duration(seconds: float) -> str:
    hours, rem = divmod(int(seconds), 3600)
    minutes, _ = divmod(rem, 60)
    return f"{hours}h {minutes}m"

bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()

MENU_BTN_STATUS = "✅ Поточний статус"
MENU_BTN_HISTORY = "📜 Історія відключень"
MENU_BTN_STOP = "🛑 Відписатися"

def build_main_menu() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text=MENU_BTN_STATUS),
                types.KeyboardButton(text=MENU_BTN_HISTORY),
            ],
            [
                types.KeyboardButton(text=MENU_BTN_STOP),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію",
    )

async def send_status(message: types.Message) -> None:
    current_state = await check_plug_status()
    last_event = await get_last_event()

    if not last_event:
        await message.answer("⚠️ Немає даних про стан електроенергії", reply_markup=build_main_menu())
        return

    last_time = last_event.get('timestamp')
    now = time.time()
    duration = now - last_time
    time_str = format_duration(duration)

    if current_state:
        status_emoji = "✅"
        status_text = "**Світло Є**"
        duration_text = f"💡 Світло доступне вже: `{time_str}`"
    else:
        status_emoji = "❌"
        status_text = "**Світла НЕМАЄ**"
        duration_text = f"🌑 Без світла вже: `{time_str}`"

    await message.answer(
        f"{status_emoji} {status_text}\n\n{duration_text}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_main_menu(),
    )

async def send_history(message: types.Message) -> None:
    events = await get_power_events(limit=250)
    if not events:
        await message.answer("⚠️ Немає історії відключень", reply_markup=build_main_menu())
        return

    kyiv_tz = pytz.timezone(Config.TIMEZONE)
    events_chrono = list(reversed(events))

    outages: list[tuple[datetime, datetime | None]] = []
    current_off: datetime | None = None

    for event in events_chrono:
        state = event.get('state')
        created_at = event.get('created_at')
        if not isinstance(created_at, datetime):
            continue

        created_at_kyiv = created_at.astimezone(kyiv_tz)

        if state == 'off':
            if current_off is None:
                current_off = created_at_kyiv
        elif state == 'on':
            if current_off is not None:
                outages.append((current_off, created_at_kyiv))
                current_off = None

    if current_off is not None:
        outages.append((current_off, None))

    if not outages:
        await message.answer("⚠️ Немає зафіксованих відключень", reply_markup=build_main_menu())
        return

    now_kyiv = datetime.now(tz=kyiv_tz)
    last_outages = outages[-10:]
    lines: list[str] = []
    for idx, (start, end) in enumerate(last_outages, start=1):
        start_str = start.strftime('%d.%m %H:%M')
        if end is None:
            duration = (now_kyiv - start).total_seconds()
            lines.append(f"{idx}. ❌ {start_str} — зараз (`{format_duration(duration)}`)")
        else:
            end_str = end.strftime('%d.%m %H:%M')
            duration = (end - start).total_seconds()
            lines.append(f"{idx}. ❌ {start_str} — ✅ {end_str} (`{format_duration(duration)}`)")

    text = "📜 **Історія відключень (останні 10):**\n\n" + "\n".join(lines)
    await message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_main_menu(),
    )

async def do_stop(message: types.Message) -> None:
    await deactivate_user(message.chat.id)
    await message.answer(
        "👋 Ти відписався від сповіщень.\n"
        "Щоб знову підписатися, використай /start",
        reply_markup=build_main_menu(),
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    await message.answer(
        "👋 Привіт! Я бот моніторингу світла.\n\n"
        "Я буду повідомляти тебе про зміни стану електроенергії.\n"
        "Користуйся кнопками меню нижче 👇\n\n"
        "Команди:\n"
        "/start - Підписатися на сповіщення\n"
        "/stop - Відписатися від сповіщень",
        reply_markup=build_main_menu(),
    )

async def setup_bot_commands(bot_instance: Bot) -> None:
    await bot_instance.set_my_commands(
        [
            types.BotCommand(command="start", description="Підписатися на сповіщення"),
            types.BotCommand(command="history", description="Історія відключень"),
            types.BotCommand(command="stop", description="Відписатися"),
        ]
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    try:
        await send_status(message)
    except Exception as e:
        logger.exception(f"Error in /status command: {e}")
        await message.answer("❌ Помилка при перевірці статусу", reply_markup=build_main_menu())

@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    try:
        await send_history(message)
    except Exception as e:
        logger.exception(f"Error in /history command: {e}")
        await message.answer("❌ Помилка при завантаженні історії", reply_markup=build_main_menu())

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if message.from_user.id != int(Config.ADMIN_USER_ID):
        await message.answer("❌ У тебе немає доступу до цієї команди")
        return
    
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer(
            "📢 **Команда для розсилки**\n\n"
            "Використання:\n"
            "`/broadcast Текст повідомлення`\n\n"
            "Приклад:\n"
            "`/broadcast 🎉 Оновлення бота: додано команду /status`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await message.answer("📤 Надсилаю повідомлення всім користувачам...")
    await broadcast_message(bot, text)
    await message.answer("✅ Розсилка завершена!")

@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    await do_stop(message)

@dp.message(F.text == MENU_BTN_STATUS)
async def status_button(message: types.Message):
    try:
        await send_status(message)
    except Exception as e:
        logger.exception(f"Error in status button: {e}")
        await message.answer("❌ Помилка при перевірці статусу", reply_markup=build_main_menu())

@dp.message(F.text == MENU_BTN_HISTORY)
async def history_button(message: types.Message):
    try:
        await send_history(message)
    except Exception as e:
        logger.exception(f"Error in history button: {e}")
        await message.answer("❌ Помилка при завантаженні історії", reply_markup=build_main_menu())

@dp.message(F.text == MENU_BTN_STOP)
async def stop_button(message: types.Message):
    await do_stop(message)

async def broadcast_message(bot_instance: Bot, text: str):
    users = await get_active_users()
    count = 0
    for user_id in users:
        try:
            await bot_instance.send_message(user_id, text, parse_mode=ParseMode.MARKDOWN)
            await log_notification(user_id, text, "sent")
            count += 1
        except TelegramForbiddenError:
            await deactivate_user(user_id)
            await log_notification(user_id, text, "user_blocked")
        except Exception as e:
            await log_notification(user_id, text, "failed")
            logger.error(f"Failed to send to {user_id}: {e}")
    
    logger.info(f"Message sent to {count} users.")

async def start_bot():
    await setup_bot_commands(bot)
    await dp.start_polling(bot)
