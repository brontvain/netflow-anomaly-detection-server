.PHONY: help install dev-install run test lint format clean docker-build docker-up docker-down migrate

help:
	@echo "Available commands:"
	@echo "  install       - Install production dependencies"
	@echo "  dev-install   - Install development dependencies"
	@echo "  run           - Run the application"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linting checks"
	@echo "  format        - Format code"
	@echo "  clean         - Clean up temporary files"
	@echo "  docker-build  - Build Docker images"
	@echo "  docker-up     - Start Docker services"
	@echo "  docker-down   - Stop Docker services"
	@echo "  migrate       - Run database migrations"

install:
	pip install -r requirements.txt

dev-install: install
	pip install pytest pytest-cov pytest-asyncio black flake8 mypy

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest --cov=app --cov-report=html --cov-report=term

lint:
	flake8 app --max-line-length=127
	mypy app --ignore-missing-imports

format:
	black app scripts

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f backend

migrate:
	python scripts/migrate_db.py

init-db:
	python scripts/init_db.py
