# Makefile for snapback development

# Auto-detect container runtime (podman preferred, fallback to docker)
CONTAINER_RUNTIME ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null || echo "podman")
COMPOSE_CMD ?= $(shell command -v podman-compose 2>/dev/null || command -v docker-compose 2>/dev/null || echo "docker-compose")

.PHONY: help install install-dev test test-coverage lint format clean build
.PHONY: docker-build docker-test docker-test-extreme docker-shell docker-clean docker-bench
.PHONY: podman-build podman-test podman-shell container-build container-test

help:
	@echo "Snapback Development Commands:"
	@echo ""
	@echo "Installation & Development:"
	@echo "  make install           - Install snapback using uv"
	@echo "  make install-dev       - Install in development mode with dev dependencies"
	@echo "  make test              - Run tests with pytest"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo "  make lint              - Run code quality checks (ruff)"
	@echo "  make format            - Format code with ruff"
	@echo "  make clean             - Remove build artifacts and cache files"
	@echo "  make build             - Build distribution packages"
	@echo "  make pre-commit        - Run all checks before committing"
	@echo ""
	@echo "Container Testing (Auto-detects podman/docker):"
	@echo "  make container-build   - Build container image (auto-detect runtime)"
	@echo "  make container-test    - Run tests in container (auto-detect)"
	@echo "  make docker-build      - Build Docker container image"
	@echo "  make docker-test       - Run tests in Docker container"
	@echo "  make docker-test-extreme - Run extreme test scenarios in Docker"
	@echo "  make docker-shell      - Open interactive shell in Docker container"
	@echo "  make docker-bench      - Run performance benchmarks in Docker"
	@echo "  make docker-clean      - Clean up Docker containers, images, and volumes"
	@echo "  make podman-build      - Build Podman container image"
	@echo "  make podman-test       - Run tests in Podman container"
	@echo "  make podman-shell      - Open interactive shell in Podman container"
	@echo ""
	@echo "Current container runtime: $(CONTAINER_RUNTIME)"
	@echo ""

install:
	uv pip install .

install-dev:
	uv pip install -e ".[dev]"

test:
	pytest -v tests/

test-coverage:
	pytest --cov=snapback --cov-report=html --cov-report=term tests/
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:
	python -m build

# Run all checks before committing
pre-commit: format lint test
	@echo ""
	@echo "All checks passed! Ready to commit."

# Container targets (auto-detect podman/docker)
container-build:
	@echo "Building with $(CONTAINER_RUNTIME)..."
	$(CONTAINER_RUNTIME) build -t snapback:test -f Dockerfile --target test .
	@echo ""
	@echo "Image built successfully: snapback:test"

container-test:
	@echo "Running tests with $(CONTAINER_RUNTIME)..."
	$(CONTAINER_RUNTIME) run --rm snapback:test

# Docker-specific targets
docker-build:
	docker build -t snapback:test -f Dockerfile --target test .
	docker build -t snapback:runtime -f Dockerfile --target runtime .
	@echo ""
	@echo "Docker images built: snapback:test, snapback:runtime"

docker-test:
	docker run --rm snapback:test

docker-test-extreme:
	@echo "Running extreme test scenarios..."
	docker run --rm \
		-e VERBOSE=1 \
		snapback:test \
		/app/docker/test-scenarios.sh

docker-shell:
	docker run --rm -it \
		-v ./src:/app/src:ro \
		-v ./tests:/app/tests:ro \
		snapback:test /bin/bash

docker-bench:
	@echo "Running performance benchmarks..."
	docker run --rm snapback:test \
		bash -c "time pytest tests/ -v"

docker-clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v 2>/dev/null || true
	docker rm -f snapback-test snapback-extreme 2>/dev/null || true
	docker volume prune -f
	docker image rm snapback:test snapback:runtime 2>/dev/null || true
	@echo "Docker cleanup complete"

# Podman-specific targets
podman-build:
	podman build -t snapback:test -f Dockerfile --target test .
	podman build -t snapback:runtime -f Dockerfile --target runtime .
	@echo ""
	@echo "Podman images built: snapback:test, snapback:runtime"

podman-test:
	podman run --rm snapback:test

podman-test-extreme:
	@echo "Running extreme test scenarios..."
	podman run --rm \
		-e VERBOSE=1 \
		snapback:test \
		/app/docker/test-scenarios.sh

podman-shell:
	podman run --rm -it \
		-v ./src:/app/src:ro \
		-v ./tests:/app/tests:ro \
		snapback:test /bin/bash

podman-clean:
	@echo "Cleaning up Podman resources..."
	podman rm -f snapback-test snapback-extreme 2>/dev/null || true
	podman volume prune -f
	podman image rm snapback:test snapback:runtime 2>/dev/null || true
	@echo "Podman cleanup complete"
