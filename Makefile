.PHONY: install install-dev setup test lint format clean dev build-ui run

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

test: ## Run tests
	pytest

lint: ## Run linter
	ruff check src tests

format: ## Auto-fix lint issues
	ruff check --fix src tests

dev: ## Run API and frontend dev servers concurrently
	@echo "Starting FastAPI on :8000 and Vite on :5173..."
	@(cd frontend && npm run dev) & yt web --dev --no-browser --port 8000

build-ui: ## Build the frontend for production
	cd frontend && npm run build

run: ## Start the production server (API + built frontend)
	yt web

clean: ## Remove build artifacts and cache
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
