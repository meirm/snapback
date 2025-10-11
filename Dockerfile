# Multi-stage Dockerfile for snapback testing
# Supports Python 3.10, 3.11, 3.12 with rsync and development tools

# Build argument for Python version
ARG PYTHON_VERSION=3.10

# Base stage: minimal Python with system dependencies
FROM python:${PYTHON_VERSION}-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    rsync \
    vim \
    coreutils \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 snapback && \
    chown -R snapback:snapback /app

# Switch to non-root user
USER snapback

# Build stage: install uv and project dependencies
FROM base AS build

# Switch to root to install uv
USER root

# Install uv
RUN pip install --no-cache-dir uv

# Switch back to snapback user
USER snapback

# Copy project files (including README.md required by pyproject.toml)
COPY --chown=snapback:snapback pyproject.toml ./
COPY --chown=snapback:snapback README.md ./
COPY --chown=snapback:snapback src/ ./src/

# Install project dependencies
RUN uv sync

# Development/Test stage: includes dev dependencies and test tools
FROM build AS test

# Copy test files
COPY --chown=snapback:snapback tests/ ./tests/
COPY --chown=snapback:snapback Makefile ./

# Copy docker test scripts
COPY --chown=snapback:snapback docker/ ./docker/

# Install development dependencies
RUN uv sync --all-extras

# Set environment variables for testing
ENV PYTHONUNBUFFERED=1
ENV PYTEST_ADDOPTS="-v --color=yes"
ENV PATH="/app/.venv/bin:$PATH"

# Default command runs tests
CMD ["uv", "run", "pytest", "tests/", "-v"]

# Runtime stage: production-like testing environment
FROM base AS runtime

# Switch to root to install uv
USER root
RUN pip install --no-cache-dir uv
USER snapback

# Copy only necessary files from build stage
COPY --chown=snapback:snapback --from=build /app/.venv /app/.venv
COPY --chown=snapback:snapback pyproject.toml ./
COPY --chown=snapback:snapback README.md ./
COPY --chown=snapback:snapback src/ ./src/

# Install project in runtime mode
RUN uv sync --no-dev

# Create directories for snapshots and test data
RUN mkdir -p /home/snapback/.Snapshots /home/snapback/test_data

# Add metadata labels
LABEL maintainer="Meir Michanie <meirm@riunx.com>"
LABEL version="2.0.0"
LABEL description="snapback - Space-efficient snapshot-based backup system"
LABEL org.opencontainers.image.source="https://github.com/meirm/snapback"

# Set PATH to include uv environment
ENV PATH="/app/.venv/bin:$PATH"

# Default command shows help
CMD ["snapback", "--help"]
