VENV ?= venv
PID_FILE ?= .bot.pid
DB_CONTAINER ?= powerbot-db
DB_NAME ?= powerbot
DB_USER ?= powerbot
DUMP_FILE ?= dump_$(shell date +%Y%m%d_%H%M%S).sql

.PHONY: help venv install migrate start stop status logs db-dump db-restore
.DEFAULT_GOAL := help

help:
	@echo "📋 Available commands:"
	@echo ""
	@echo "  Setup:"
	@echo "    make venv          - Create virtual environment"
	@echo "    make install       - Install dependencies"
	@echo "    make migrate       - Apply database migrations"
	@echo ""
	@echo "  Bot control:"
	@echo "    make start         - Start bot in background"
	@echo "    make stop          - Stop bot"
	@echo "    make status        - Check bot status"
	@echo "    make logs          - View current logs"
	@echo ""
	@echo "  Database:"
	@echo "    make db-dump       - Create DB dump (DUMP_FILE=filename.sql)"
	@echo "    make db-restore    - Restore DB from dump (DUMP=filename.sql)"
	@echo ""

# Setup
venv:
	python3 -m venv $(VENV)
	. $(VENV)/bin/activate && pip install --upgrade pip

install: venv
	. $(VENV)/bin/activate && pip install -r requirements.txt

migrate:
	. $(VENV)/bin/activate && python app/migrate.py

# Bot control
start:
	@if [ -f $(PID_FILE) ]; then \
		echo "❌ Bot already running (PID: $$(cat $(PID_FILE)))"; \
		exit 1; \
	fi
	@echo "🚀 Starting bot in background..."
	@. $(VENV)/bin/activate && python app/main.py > /dev/null 2>&1 & \
	sleep 0.5 && \
	pgrep -f "python.*app/main.py" | tail -1 > $(PID_FILE)
	@echo "✅ Bot started (PID: $$(cat $(PID_FILE)))"
	@echo "📋 Logs: tail -f logs/bot_$$(date +%Y-%m-%d).log"

stop:
	@if [ ! -f $(PID_FILE) ]; then \
		echo "❌ Bot not running (no PID file)"; \
		echo "Try: pkill -f 'python.*main.py'"; \
		exit 1; \
	fi
	@echo "🛑 Stopping bot..."
	@PID=$$(cat $(PID_FILE)); \
	if ps -p $$PID > /dev/null 2>&1; then \
		kill $$PID && sleep 1; \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "⚠️  Process didn't stop, using SIGKILL..."; \
			kill -9 $$PID; \
		fi; \
		rm $(PID_FILE); \
		echo "✅ Bot stopped"; \
	else \
		echo "⚠️  Process not found, removing stale PID file"; \
		rm $(PID_FILE); \
	fi

status:
	@if [ ! -f $(PID_FILE) ]; then \
		echo "❌ Bot not running"; \
	else \
		if ps -p $$(cat $(PID_FILE)) > /dev/null; then \
			echo "✅ Bot running (PID: $$(cat $(PID_FILE)))"; \
		else \
			echo "❌ Bot not running (stale PID file)"; \
			rm $(PID_FILE); \
		fi \
	fi

logs:
	@LOG_FILE=logs/bot_$$(date +%Y-%m-%d).log; \
	if [ -f $$LOG_FILE ]; then \
		tail -f $$LOG_FILE; \
	else \
		echo "❌ Log file not found: $$LOG_FILE"; \
		echo "Available logs:"; \
		ls -1 logs/ 2>/dev/null || echo "logs/ folder is empty"; \
	fi

# Database
db-dump:
	@echo "📦 Creating database dump..."
	@docker exec $(DB_CONTAINER) pg_dump -U $(DB_USER) $(DB_NAME) > $(DUMP_FILE)
	@echo "✅ Dump saved to: $(DUMP_FILE)"

db-restore:
	@if [ -z "$(DUMP)" ]; then \
		echo "❌ Specify dump file: make db-restore DUMP=filename.sql"; \
		exit 1; \
	fi
	@if [ ! -f "$(DUMP)" ]; then \
		echo "❌ File not found: $(DUMP)"; \
		exit 1; \
	fi
	@echo "⚠️  Restoring database from $(DUMP)..."
	@docker exec -i $(DB_CONTAINER) psql -U $(DB_USER) $(DB_NAME) < $(DUMP)
	@echo "🔄 Resetting sequences..."
	@docker exec $(DB_CONTAINER) psql -U $(DB_USER) $(DB_NAME) -c \
		"SELECT setval(pg_get_serial_sequence('power_events', 'id'), COALESCE(MAX(id), 1)) FROM power_events;" > /dev/null
	@echo "✅ Database restored from: $(DUMP)"
