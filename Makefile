# Research Agent - Development Commands
# Usage: make [target]

SHELL := /bin/bash
BACKEND_VENV := backend/venv/bin
BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: dev backend frontend stop restart logs clean help status

# Default target
help:
	@echo "Research Agent Development Commands"
	@echo ""
	@echo "  make dev        - Start both backend and frontend"
	@echo "  make backend    - Start only the backend"
	@echo "  make frontend   - Start only the frontend"
	@echo "  make stop       - Stop all running services"
	@echo "  make restart    - Restart all services"
	@echo "  make status     - Check service status"
	@echo "  make logs       - Show backend logs"
	@echo "  make test       - Run backend tests"
	@echo "  make clean      - Remove PID and log files"
	@echo ""

# Start both services
dev: stop
	@echo "Starting Research Agent..."
	@$(MAKE) backend-bg
	@$(MAKE) frontend-bg
	@echo ""
	@echo "Services started!"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo ""
	@echo "Use 'make stop' to stop all services"
	@echo "Use 'make logs' to view backend logs"

# Start backend in foreground (useful for debugging)
backend:
	@echo "Starting backend..."
	cd $(BACKEND_DIR) && $(CURDIR)/$(BACKEND_VENV)/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend in foreground
frontend:
	@echo "Starting frontend..."
	cd $(FRONTEND_DIR) && npm run dev

# Start backend in background
backend-bg:
	@echo "Starting backend in background..."
	@cd $(BACKEND_DIR) && $(CURDIR)/$(BACKEND_VENV)/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > $(CURDIR)/backend.log 2>&1 & echo $$! > $(CURDIR)/backend.pid
	@sleep 2
	@if [ -f backend.pid ] && kill -0 $$(cat backend.pid) 2>/dev/null; then \
		echo "Backend started (PID: $$(cat backend.pid))"; \
	else \
		echo "Backend failed to start. Check backend.log"; \
		cat backend.log | tail -20; \
	fi

# Start frontend in background
frontend-bg:
	@echo "Starting frontend in background..."
	@cd $(FRONTEND_DIR) && npm run dev > $(CURDIR)/frontend.log 2>&1 & echo $$! > $(CURDIR)/frontend.pid
	@sleep 3
	@if [ -f frontend.pid ] && kill -0 $$(cat frontend.pid) 2>/dev/null; then \
		echo "Frontend started (PID: $$(cat frontend.pid))"; \
	else \
		echo "Frontend failed to start. Check frontend.log"; \
		cat frontend.log | tail -20; \
	fi

# Stop all services
stop:
	@echo "Stopping services..."
	@-fuser -k 8000/tcp 2>/dev/null || true
	@-fuser -k 5173/tcp 2>/dev/null || true
	@-pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@-pkill -f "node.*vite" 2>/dev/null || true
	@-rm -f backend.pid frontend.pid
	@sleep 1
	@echo "All services stopped"

# Restart all services
restart: stop dev

# View backend logs
logs:
	@if [ -f backend.log ]; then \
		tail -f backend.log; \
	else \
		echo "No backend.log found. Start services with 'make dev' first."; \
	fi

# View frontend logs
logs-frontend:
	@if [ -f frontend.log ]; then \
		tail -f frontend.log; \
	else \
		echo "No frontend.log found. Start services with 'make dev' first."; \
	fi

# Run backend tests
test:
	cd $(BACKEND_DIR) && $(CURDIR)/$(BACKEND_VENV)/python -m pytest tests/ -v

# Clean up PID and log files
clean: stop
	@rm -f backend.pid frontend.pid backend.log frontend.log
	@echo "Cleaned up PID and log files"

# Check status
status:
	@echo "Service Status:"
	@if pgrep -f "uvicorn app.main:app" > /dev/null; then \
		echo "  Backend:  Running"; \
	else \
		echo "  Backend:  Stopped"; \
	fi
	@if pgrep -f "node.*vite" > /dev/null; then \
		echo "  Frontend: Running"; \
	else \
		echo "  Frontend: Stopped"; \
	fi
