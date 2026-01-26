# Power Bot 🔌⚡

Telegram bot for power monitoring via Tapo Smart Plug.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Bot Commands](#bot-commands)
- [Project Structure](#project-structure)
- [Development](#development)
- [Database Migrations](#database-migrations)
- [Makefile Commands](#makefile-commands)
- [Troubleshooting](#troubleshooting)
- [Technologies](#technologies)
- [License](#license)

## Features

- 📊 **Power status monitoring** via Tapo Smart Plug
- 💾 **Event history storage** in PostgreSQL
- 📱 **User notifications** via Telegram about status changes
- ⏱️ **Duration display** for outages/power availability
- 📜 **Outage history view** for recent period
- 👥 **Subscribe/unsubscribe** from notifications
- 🔧 **CLI tools** for administration

## Requirements

- Python 3.11+
- PostgreSQL 15+
- Git
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Tapo Smart Plug with local network access

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/dixydo/powerbot.git
cd powerbot
```

### 2. Configure environment variables

Create `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```bash
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_USER_ID=your_telegram_user_id

# Tapo Device Configuration
TAPO_EMAIL=your_tapo_email@example.com
TAPO_PASSWORD=your_tapo_password
DEVICE_IP=192.168.1.100

# Monitoring Settings
CHECK_INTERVAL=30
TIMEZONE=Europe/Kyiv

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=powerbot
DB_USER=powerbot
DB_PASSWORD=powerbot
```

**How to get Bot Token:**
1. Find [@BotFather](https://t.me/botfather) in Telegram
2. Send `/newbot` command
3. Follow instructions and save the token

**How to find your User ID:**
1. Find [@userinfobot](https://t.me/userinfobot) in Telegram
2. Send `/start` and get your ID

### 3. Install dependencies

```bash
make install
```

### 4. Configure PostgreSQL

Make sure PostgreSQL is running and accessible on `localhost:5432`.

Create database and user:

```sql
CREATE DATABASE powerbot;
CREATE USER powerbot WITH PASSWORD 'powerbot';
GRANT ALL PRIVILEGES ON DATABASE powerbot TO powerbot;
\c powerbot
GRANT ALL ON SCHEMA public TO powerbot;
```

**Note:** The `\c powerbot` command connects to the database, and `GRANT ALL ON SCHEMA public` grants rights to the public schema, which is required for creating tables.

### 5. Apply migrations

```bash
make migrate
```

### 6. Start the bot

**Background mode (recommended):**

```bash
make start
```

Bot will start in background. Logs will be written to `logs` folder.

**Other commands:**

```bash
make stop      # Stop bot
make status    # Check bot status
make logs      # View current logs
```

**View logs:**

```bash
# Current logs
tail -f logs/bot_$(date +%Y-%m-%d).log

# Or all logs for today
cat logs/bot_$(date +%Y-%m-%d).log

# Logs for specific date
cat logs/bot_2026-01-25.log
```

Logs automatically rotate daily at midnight. Logs are kept for the last 30 days.

## Configuration

### Tapo Smart Plug Setup

1. Connect your Tapo Smart Plug to Wi-Fi via Tapo mobile app
2. Find device IP address:
   - Via Tapo app (Device Info)
   - Via router web interface
   - Using `arp -a` command or other network utilities
3. Prepare email and password from Tapo account

### Timezone Configuration

By default, the bot uses `Europe/Kyiv` timezone. You can change it in `.env`:

```bash
TIMEZONE=Europe/Kyiv  # or another timezone, e.g. America/New_York
```

Timezone is used for:
- Displaying time in outage history
- Event logging
- Log file rotation

### Database Configuration

For production use, it's recommended to:
- Use separate PostgreSQL server
- Change passwords in `.env` to secure ones
- Configure backups

## Bot Commands

Bot supports both slash commands and menu buttons:

### Slash Commands

- `/start` - Subscribe to notifications
- `/status` - Check current power status
- `/history` - View outage history
- `/stop` - Unsubscribe from notifications
- `/broadcast <text>` - Send message to all users (admin only)

### Menu Buttons

- ✅ **Current Status** - Check power status
- 📜 **View Outage History** - View last 10 outages
- 🛑 **Unsubscribe** - Unsubscribe from notifications

## Project Structure

```
power-bot/
├── app/
│   ├── main.py              # Main application entry point
│   ├── bot.py               # Telegram bot handlers
│   ├── monitor.py           # Power monitoring loop
│   ├── database.py          # Database operations
│   ├── config.py            # Configuration and logging
│   ├── migrate.py           # Migration runner
│   └── migrations/          # SQL migrations
│       ├── 001_create_users.sql
│       ├── 002_create_power_events.sql
│       └── 003_create_notifications.sql
├── logs/                    # Log files (auto-created)
├── .env                     # Environment variables (create from .env.example)
├── .env.example             # Environment variables template
├── .gitignore              # Git ignore rules
├── requirements.txt         # Python dependencies
├── Makefile                # Development commands
├── LICENSE                 # MIT License
└── README.md               # This file
```

## Development

### Local Development

1. **Create virtual environment:**
   ```bash
   make venv
   ```

2. **Install dependencies:**
   ```bash
   make install
   ```

3. **Apply migrations:**
   ```bash
   make migrate
   ```

4. **Start bot:**
   ```bash
   make start
   ```

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for functions
- Use async/await for I/O operations

## Database Migrations

### Migration System

Project uses custom migration system based on SQL files. Migrations are located in `app/migrations/` directory.

### Migration File Format

```
NNN_description.sql
```

Where:
- `NNN` - sequential number (001, 002, etc.)
- `description` - brief description

### Creating New Migration

1. Create new file in `app/migrations/`:
   ```bash
   touch app/migrations/005_add_new_table.sql
   ```

2. Write SQL:
   ```sql
   CREATE TABLE new_table (
       id BIGSERIAL PRIMARY KEY,
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );
   ```

3. Apply migration:
   ```bash
   make migrate
   ```

### schema_migrations Table

Project automatically creates `schema_migrations` table to track applied migrations:

```sql
CREATE TABLE schema_migrations (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Makefile Commands

### Virtual Environment

```bash
make venv          # Create virtual environment
make install       # Install dependencies
```

### Bot Control

```bash
make start         # Start bot in background
make stop          # Stop bot
make status        # Check bot status
make logs          # View current logs
```

### Database

```bash
make migrate       # Apply migrations
```

## Troubleshooting

### PostgreSQL Connection Issues

1. Check if database is running:
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. Verify credentials in `.env`

3. Check PostgreSQL logs

4. Try applying migrations again

### Tapo Smart Plug Not Responding

1. Check device IP address in `.env`
2. Make sure device is on same network
3. Verify email/password from Tapo account
4. Try rebooting Smart Plug

### How to Stop Bot

```bash
make stop
```

## Technologies

### Backend

- **Python 3.11+** - main programming language
- **aiogram 3.24.0** - Telegram Bot API framework
- **psycopg 3** - PostgreSQL adapter for Python
- **tapo 0.8.8** - API for Tapo Smart Plug control
- **pytz 2025.2** - timezone handling

### Infrastructure

- **PostgreSQL 15** - relational database
- **Make** - development command automation

### Architecture

- Asynchronous architecture based on `asyncio`
- Two parallel processes: bot + monitoring
- SQL migrations for database schema versioning
- Environment-based configuration

## License

MIT License - see [LICENSE](LICENSE) for details.
