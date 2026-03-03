.PHONY: install install-dev setup test test-ui test-all lint format clean dev build-ui run

install: ## Install the package
	uv venv
	uv pip install -e .
	playwright install chromium

install-dev: ## Install with dev dependencies
	uv venv
	uv pip install -e ".[dev]"
	playwright install chromium

setup: install-dev ## Full setup: install + init database + auth
	yt db init
	yt auth setup

test: ## Run backend tests
	pytest

test-ui: ## Run frontend tests
	cd frontend && npx vitest run

test-all: ## Run backend and frontend tests
	pytest -v
	cd frontend && npx vitest run

lint: ## Run linter
	ruff check src tests

format: ## Auto-fix lint issues
	ruff check --fix src tests

dev: ## Run API + frontend dev servers
	@echo "Starting FastAPI on :8000 and Vite on :5173..."
	@trap 'kill 0' EXIT; \
	(yt web --dev --no-browser --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

build-ui: ## Build frontend for production
	cd frontend && npm install && npm run build

run: build-ui ## Build frontend and start production server
	yt web

clean: ## Remove build artifacts and cache
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
