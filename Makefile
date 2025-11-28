.PHONY: test test-unit test-integration test-cov test-fast clean help docker-build docker-run docker-stop docker-logs docker-clean compose-up compose-down compose-logs compose-restart

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

test:  ## Run all tests
	pytest tests/ -v

test-unit:  ## Run unit tests only
	pytest tests/test_document_processor.py -v -m unit

test-integration:  ## Run integration tests only
	pytest tests/integration/ -v -m integration

test-fast:  ## Run fast tests (skip slow tests)
	pytest tests/ -v -m "not slow"

test-cov:  ## Run tests with coverage report
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated: htmlcov/index.html"

test-cov-html:  ## Run tests with coverage and open HTML report
	pytest tests/ -v --cov=app --cov-report=html
	@echo "Opening coverage report..."
	@python -m webbrowser htmlcov/index.html || xdg-open htmlcov/index.html || open htmlcov/index.html

clean:  ## Clean test artifacts and cache
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleaned test artifacts"

install:  ## Install dependencies
	pip install -r requirements.txt
	@echo "Dependencies installed"

run:  ## Run the FastAPI application
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod:  ## Run the FastAPI application in production mode
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# ============================================
# Docker Commands
# ============================================

docker-build:  ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t legal-document-chunking-api:latest .
	@echo "✅ Image built successfully"
	@docker images legal-document-chunking-api:latest

docker-run:  ## Run Docker container
	@echo "🚀 Starting Docker container..."
	docker run -d \
		--name legal-document-chunking-api \
		--env-file .env \
		-p 8000:8000 \
		--restart unless-stopped \
		legal-document-chunking-api:latest
	@echo "✅ Container started"
	@echo "📊 View logs with: make docker-logs"

docker-stop:  ## Stop and remove Docker container
	@echo "🛑 Stopping container..."
	docker stop legal-document-chunking-api 2>/dev/null || true
	docker rm legal-document-chunking-api 2>/dev/null || true
	@echo "✅ Container stopped"

docker-logs:  ## Show Docker container logs
	docker logs -f legal-document-chunking-api

docker-clean:  ## Clean Docker resources
	@echo "🧹 Cleaning Docker resources..."
	docker system prune -f
	@echo "✅ Cleaned"

# ============================================
# Docker Compose Commands
# ============================================

compose-up:  ## Start services with docker-compose
	@echo "🚀 Starting services..."
	docker-compose up -d
	@echo "✅ Services started"

compose-down:  ## Stop services with docker-compose
	@echo "🛑 Stopping services..."
	docker-compose down
	@echo "✅ Services stopped"

compose-logs:  ## Show docker-compose logs
	docker-compose logs -f api

compose-restart:  ## Restart docker-compose services
	@echo "🔄 Restarting services..."
	docker-compose restart api
	@echo "✅ Services restarted"

compose-build:  ## Rebuild and start services
	@echo "🔨 Rebuilding services..."
	docker-compose up -d --build
	@echo "✅ Services rebuilt and started"
