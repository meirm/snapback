# Container Testing Guide for snapback

Comprehensive guide for testing snapback using **Podman** (recommended) or Docker in isolated container environments, including extreme stress testing scenarios.

## Table of Contents

- [Quick Start](#quick-start)
- [Podman Instructions (Primary)](#podman-instructions-primary)
- [Docker Instructions (Alternative)](#docker-instructions-alternative)
- [Test Scenarios](#test-scenarios)
- [Performance Benchmarking](#performance-benchmarking)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)
- [Advanced Usage](#advanced-usage)

## Quick Start

### Podman (Recommended)

```bash
# Build the image
podman build -t snapback:test -f Dockerfile .

# Run unit tests
podman run --rm snapback:test

# Run extreme scenarios
podman run --rm -v ./docker:/app/docker:ro snapback:test /app/docker/test-scenarios.sh
```

### Docker

```bash
# Build the image
docker build -t snapback:test -f Dockerfile .

# Run unit tests
docker run --rm snapback:test

# Use docker-compose for all services
docker-compose run snapback-test
```

## Podman Instructions (Primary)

Podman is our recommended container runtime because:
- **Rootless by default**: More secure, no daemon required
- **Docker-compatible**: Same command syntax as Docker
- **Pod support**: Can create Kubernetes-style pods
- **No daemon**: Lightweight, direct fork-exec model

### Installation

**macOS:**
```bash
brew install podman
podman machine init
podman machine start
```

**Linux (RHEL/Fedora/CentOS):**
```bash
sudo dnf install podman
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install podman
```

### Building Images

**Standard test image:**
```bash
podman build -t snapback:test -f Dockerfile --target test .
```

**Runtime image:**
```bash
podman build -t snapback:runtime -f Dockerfile --target runtime .
```

**Python version matrix:**
```bash
# Python 3.10 (default)
podman build -t snapback:test-py310 --build-arg PYTHON_VERSION=3.10 .

# Python 3.11
podman build -t snapback:test-py311 --build-arg PYTHON_VERSION=3.11 .

# Python 3.12
podman build -t snapback:test-py312 --build-arg PYTHON_VERSION=3.12 .
```

### Running Tests

**Quick unit tests:**
```bash
podman run --rm snapback:test
```

**With coverage:**
```bash
podman run --rm snapback:test uv run pytest tests/ --cov=src/snapback --cov-report=html
```

**Interactive shell:**
```bash
podman run --rm -it snapback:test /bin/bash
```

**Mount local code for development:**
```bash
podman run --rm \
  -v ./src:/app/src:ro \
  -v ./tests:/app/tests:ro \
  snapback:test
```

### Running Extreme Scenarios

**Generate test data:**
```bash
podman run --rm \
  -v snapback-test-data:/home/snapback/test_data \
  snapback:test \
  /app/docker/generate-test-data.sh
```

**Run all extreme test scenarios:**
```bash
podman run --rm \
  -v snapback-test-data:/home/snapback/test_data \
  -v snapback-snapshots:/home/snapback/.Snapshots \
  -e VERBOSE=1 \
  snapback:test \
  /app/docker/test-scenarios.sh
```

**Run specific test:**
```bash
podman run --rm \
  -v snapback-test-data:/home/snapback/test_data \
  -v snapback-snapshots:/home/snapback/.Snapshots \
  snapback:test \
  bash -c "source /app/docker/test-scenarios.sh && test_large_file_backup"
```

### Podman-Specific Features

**Using pods for complex scenarios:**
```bash
# Create a pod
podman pod create --name snapback-pod -p 8080:8080

# Run containers in the pod
podman run -d --pod snapback-pod --name snapback-app snapback:runtime
podman run -d --pod snapback-pod --name snapback-monitor monitoring-image
```

**Rootless mode considerations:**
```bash
# Check if running rootless
podman info | grep rootless

# Run with specific user namespace
podman run --rm --userns=keep-id snapback:test
```

**Volume management:**
```bash
# List volumes
podman volume ls

# Create named volume
podman volume create snapback-test-data

# Inspect volume
podman volume inspect snapback-test-data

# Remove volumes
podman volume rm snapback-test-data
podman volume prune
```

## Docker Instructions (Alternative)

Docker can be used as an alternative if Podman is not available.

### Installation

**macOS:**
```bash
brew install --cask docker
# Or download Docker Desktop from docker.com
```

**Linux:**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# RHEL/Fedora/CentOS
sudo dnf install docker-ce docker-ce-cli containerd.io
```

### Building Images

Same as Podman, but use `docker` command:

```bash
docker build -t snapback:test -f Dockerfile --target test .
docker build -t snapback:runtime -f Dockerfile --target runtime .
```

### Running Tests

**Quick unit tests:**
```bash
docker run --rm snapback:test
```

**With coverage:**
```bash
docker run --rm snapback:test uv run pytest tests/ --cov=src/snapback
```

**Interactive shell:**
```bash
docker run --rm -it snapback:test /bin/bash
```

### Using Docker Compose

**Run default test suite:**
```bash
docker-compose run --rm snapback-test
```

**Run extreme scenarios:**
```bash
docker-compose --profile extreme run --rm snapback-extreme
```

**Run performance benchmarks:**
```bash
docker-compose --profile bench run --rm snapback-bench
```

**Run Python version matrix:**
```bash
docker-compose --profile matrix run --rm snapback-py311
docker-compose --profile matrix run --rm snapback-py312
```

**Clean up:**
```bash
docker-compose down -v
```

## Test Scenarios

The test suite includes 10 extreme scenarios designed to stress-test snapback:

### Test 1: Large Single File Backup (>1GB)

**Purpose**: Verify handling of files >1GB
**Expected Behavior**: Successful backup with rsync streaming
**Success Criteria**: File backed up, hard links work, recovery succeeds

```bash
# Podman
podman run --rm snapback:test bash -c "source /app/docker/test-scenarios.sh && test_large_file_backup"

# Docker
docker run --rm snapback:test bash -c "source /app/docker/test-scenarios.sh && test_large_file_backup"
```

### Test 2: File Count Stress Test (>100k files)

**Purpose**: Test with >100k files
**Expected Behavior**: All files backed up, reasonable performance
**Success Criteria**: All files present, rotation works, space efficient

```bash
# Configure file count
podman run --rm -e HIGH_FILE_COUNT=150000 snapback:test \
  bash -c "source /app/docker/test-scenarios.sh && test_high_file_count"
```

### Test 3: Deep Nesting Test (>50 levels)

**Purpose**: Test deep directory hierarchies
**Expected Behavior**: All directories backed up
**Success Criteria**: Full path recreation, recovery works

```bash
podman run --rm -e DEEP_NESTING_LEVELS=100 snapback:test \
  bash -c "source /app/docker/test-scenarios.sh && test_deep_nesting"
```

### Test 4: Rapid Rotation Test

**Purpose**: Test all 24 hourly snapshots in <10 minutes
**Expected Behavior**: Rotation logic works correctly
**Success Criteria**: Correct snapshot promotion, no data loss

### Test 5: Full Rotation Cycle

**Purpose**: Test complete hourly → daily → weekly → monthly rotation
**Expected Behavior**: Promotion chain works correctly
**Success Criteria**: Data preserved through all tiers, oldest snapshots deleted

### Test 6: Disk Space Constraint Test

**Purpose**: Test behavior when disk is nearly full
**Expected Behavior**: Graceful failure or completion
**Success Criteria**: Clear error messages, no corruption

### Test 7: Permission Chaos Test

**Purpose**: Test various permission scenarios
**Expected Behavior**: Appropriate handling based on permissions
**Success Criteria**: Correct error handling, no crashes

### Test 8: Corruption Recovery Test

**Purpose**: Test recovery when snapshots are corrupted
**Expected Behavior**: Detection and handling of corruption
**Success Criteria**: Clear error messages, safe recovery paths

### Test 9: Hard Link Verification Test

**Purpose**: Verify hard links save space as expected
**Expected Behavior**: Space usage 1.5-3x source, not 46x
**Success Criteria**: Inode sharing verified, space calculated correctly

### Test 10: Edge Case Parameters Test

**Purpose**: Test unusual rsync parameters and configurations
**Expected Behavior**: Correct parameter handling
**Success Criteria**: Parameters applied correctly, no failures

## Performance Benchmarking

### Benchmark Commands

**Time unit tests:**
```bash
time podman run --rm snapback:test
```

**Benchmark backup operations:**
```bash
podman run --rm \
  -v snapback-bench:/home/snapback/test_data \
  snapback:test \
  bash -c "
    /app/docker/generate-test-data.sh &&
    time snapback hourly
  "
```

**Measure space efficiency:**
```bash
podman run --rm \
  -v snapback-bench:/home/snapback/test_data \
  -v snapback-snapshots:/home/snapback/.Snapshots \
  snapback:test \
  bash -c "
    snapback hourly &&
    echo 'Source size:' &&
    du -sh /home/snapback/test_data &&
    echo 'Snapshot size:' &&
    du -sh /home/snapback/.Snapshots
  "
```

### Performance Expectations

- **Unit tests**: <30 seconds
- **Quick scenario tests**: <5 minutes
- **Full test suite**: <30 minutes
- **Extreme scenarios**: <6 hours (can run overnight)
- **Image build**: <5 minutes (with cache)
- **Image size**: <500MB (slim image with dependencies)

### Resource Limits

Test with constrained resources:

**Memory limits:**
```bash
# 512MB
podman run --rm --memory=512m snapback:test

# 1GB
podman run --rm --memory=1g snapback:test
```

**CPU limits:**
```bash
# 1 core
podman run --rm --cpus=1 snapback:test

# 2 cores
podman run --rm --cpus=2 snapback:test
```

**Combined limits:**
```bash
podman run --rm \
  --memory=1g \
  --cpus=2 \
  --pids-limit=1024 \
  snapback:test
```

## Troubleshooting

### Common Issues

**Issue: Image build fails with "permission denied"**

**Podman solution:**
```bash
# Check SELinux context (Linux)
ls -Z Dockerfile

# Relabel if needed
chcon -Rt svirt_sandbox_file_t .

# Or disable SELinux temporarily
sudo setenforce 0
```

**Docker solution:**
```bash
# Ensure Docker daemon is running
sudo systemctl start docker

# Check Docker permissions
sudo usermod -aG docker $USER
newgrp docker
```

**Issue: Tests fail with "disk space" errors**

**Solution:**
```bash
# Clean up volumes
podman volume prune

# Check available space
df -h

# Use smaller test parameters
podman run --rm \
  -e HIGH_FILE_COUNT=1000 \
  -e LARGE_FILE_SIZE=100M \
  snapback:test
```

**Issue: Container exits immediately**

**Solution:**
```bash
# Check container logs
podman logs snapback-test

# Run with interactive shell
podman run --rm -it snapback:test /bin/bash

# Check entrypoint
podman inspect snapback:test | grep -A5 Entrypoint
```

**Issue: Volume mount permission errors**

**Podman solution (rootless):**
```bash
# Use :Z for SELinux relabeling
podman run --rm -v ./src:/app/src:Z snapback:test

# Or use --userns=keep-id
podman run --rm --userns=keep-id -v ./src:/app/src snapback:test
```

**Issue: Network connectivity problems**

**Solution:**
```bash
# Check network
podman network ls

# Recreate network
podman network rm snapback-network
podman network create snapback-network

# Test connectivity
podman run --rm --network snapback-network alpine ping -c 3 google.com
```

### Debugging Inside Containers

**Enter running container:**
```bash
# Podman
podman exec -it snapback-test /bin/bash

# Docker
docker exec -it snapback-test /bin/bash
```

**Inspect container:**
```bash
# View container details
podman inspect snapback-test

# View container logs
podman logs snapback-test

# View resource usage
podman stats snapback-test
```

**Run tests with verbose output:**
```bash
podman run --rm \
  -e VERBOSE=1 \
  -e PYTEST_ADDOPTS="-v -s" \
  snapback:test
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Container Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v3

      - name: Build container
        run: |
          docker build \
            --build-arg PYTHON_VERSION=${{ matrix.python-version }} \
            -t snapback:test \
            -f Dockerfile \
            --target test \
            .

      - name: Run tests
        run: docker run --rm snapback:test

      - name: Run extreme scenarios
        run: |
          docker run --rm \
            -e HIGH_FILE_COUNT=10000 \
            -e LARGE_FILE_SIZE=500M \
            snapback:test \
            /app/docker/test-scenarios.sh
```

### GitLab CI Example

```yaml
test:
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t snapback:test .
    - docker run --rm snapback:test
  only:
    - main
    - merge_requests
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'docker build -t snapback:test .'
            }
        }

        stage('Test') {
            steps {
                sh 'docker run --rm snapback:test'
            }
        }

        stage('Extreme Tests') {
            steps {
                sh '''
                    docker run --rm \
                      -e HIGH_FILE_COUNT=50000 \
                      snapback:test \
                      /app/docker/test-scenarios.sh
                '''
            }
        }
    }

    post {
        always {
            sh 'docker system prune -f'
        }
    }
}
```

## Advanced Usage

### Custom Test Scenarios

Create your own test script:

```bash
#!/bin/bash
# my-custom-test.sh

source /app/docker/test-scenarios.sh

setup_test_env

# Your custom test logic here
start_test "My Custom Test"
# ... test implementation ...
pass_test "My Custom Test"

cleanup_test
print_report
```

Run it:
```bash
podman run --rm \
  -v ./my-custom-test.sh:/app/my-test.sh:ro \
  snapback:test \
  /app/my-test.sh
```

### Extending the Dockerfile

Add custom tools:

```dockerfile
FROM snapback:test AS custom-test

USER root
RUN apt-get update && apt-get install -y \
    strace \
    htop \
    && rm -rf /var/lib/apt/lists/*

USER snapback
```

### Multi-Container Testing

Test with multiple containers:

```yaml
# custom-compose.yml
version: '3.8'

services:
  snapback-primary:
    image: snapback:test
    volumes:
      - shared-data:/home/snapback/test_data

  snapback-secondary:
    image: snapback:test
    volumes:
      - shared-data:/home/snapback/test_data:ro
    command: ["snapback", "--recover", "hour-0"]

volumes:
  shared-data:
```

### Performance Profiling

Profile Python code:

```bash
podman run --rm snapback:test \
  python -m cProfile -o /tmp/profile.stats -m pytest tests/

# View results
podman run --rm snapback:test \
  python -c "import pstats; p = pstats.Stats('/tmp/profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

### Security Scanning

Scan image for vulnerabilities:

```bash
# Using Trivy
podman run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image snapback:test

# Using Grype
grype snapback:test
```

---

**Need Help?**

- Report issues: https://github.com/meirm/snapback/issues
- Documentation: README.md
- Project home: https://github.com/meirm/snapback
