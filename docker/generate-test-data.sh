#!/usr/bin/env bash
#
# generate-test-data.sh - Generate test data for snapback container testing
#
# Creates various test scenarios including:
# - Large files (1KB to 10GB)
# - High file counts (1k to 500k files)
# - Deep directory nesting
# - Special characters in names
# - Various permissions
# - Symlinks and hard links
#

set -euo pipefail

# Configuration via environment variables
TEST_DATA_DIR="${TEST_DATA_DIR:-/home/snapback/test_data}"
LARGE_FILE_SIZE="${LARGE_FILE_SIZE:-1G}"
HIGH_FILE_COUNT="${HIGH_FILE_COUNT:-10000}"
DEEP_NESTING_LEVELS="${DEEP_NESTING_LEVELS:-50}"
VERBOSE="${VERBOSE:-0}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

info() {
    if [[ "$VERBOSE" == "1" ]]; then
        echo -e "${BLUE}[INFO]${NC} $*"
    fi
}

# Create base test data directory
create_base_structure() {
    log "Creating base test data structure at $TEST_DATA_DIR"
    mkdir -p "$TEST_DATA_DIR"
    cd "$TEST_DATA_DIR"
}

# Generate large files of various sizes
generate_large_files() {
    local dir="$TEST_DATA_DIR/large_files"
    log "Generating large files in $dir"
    mkdir -p "$dir"

    # Create files of different sizes
    info "Creating 1KB file..."
    dd if=/dev/urandom of="$dir/file_1KB.bin" bs=1K count=1 2>/dev/null

    info "Creating 1MB file..."
    dd if=/dev/urandom of="$dir/file_1MB.bin" bs=1M count=1 2>/dev/null

    info "Creating 10MB file..."
    dd if=/dev/urandom of="$dir/file_10MB.bin" bs=1M count=10 2>/dev/null

    info "Creating 100MB file..."
    dd if=/dev/urandom of="$dir/file_100MB.bin" bs=1M count=100 2>/dev/null

    if [[ "${LARGE_FILE_SIZE}" == *"G"* ]]; then
        local size_gb="${LARGE_FILE_SIZE//G/}"
        info "Creating ${size_gb}GB file..."
        dd if=/dev/urandom of="$dir/file_${size_gb}GB.bin" bs=1M count=$((size_gb * 1024)) 2>/dev/null
    fi

    log "Large files created: $(ls -lh "$dir" | wc -l) files"
}

# Generate high file count directories
generate_high_file_count() {
    local dir="$TEST_DATA_DIR/high_file_count"
    log "Generating $HIGH_FILE_COUNT files in $dir"
    mkdir -p "$dir"

    for i in $(seq 1 "$HIGH_FILE_COUNT"); do
        echo "Content $i" > "$dir/file_$(printf "%06d" $i).txt"
        if [[ $((i % 1000)) -eq 0 ]]; then
            info "Created $i files..."
        fi
    done

    log "High file count directory created: $HIGH_FILE_COUNT files"
}

# Generate deeply nested directory structure
generate_deep_nesting() {
    local dir="$TEST_DATA_DIR/deep_nesting"
    log "Generating deep nesting ($DEEP_NESTING_LEVELS levels) in $dir"
    mkdir -p "$dir"

    local current_dir="$dir"
    for i in $(seq 1 "$DEEP_NESTING_LEVELS"); do
        current_dir="$current_dir/level_$(printf "%03d" $i)"
        mkdir -p "$current_dir"
        echo "Level $i content" > "$current_dir/file.txt"
    done

    log "Deep nesting created: $DEEP_NESTING_LEVELS levels"
}

# Generate files with special characters
generate_special_chars() {
    local dir="$TEST_DATA_DIR/special_chars"
    log "Generating files with special characters in $dir"
    mkdir -p "$dir"

    # Create files with various special characters
    touch "$dir/file with spaces.txt"
    touch "$dir/file_with_underscores.txt"
    touch "$dir/file-with-dashes.txt"
    touch "$dir/file.multiple.dots.txt"
    touch "$dir/file'with'quotes.txt"
    touch "$dir/file[with]brackets.txt"
    touch "$dir/file(with)parens.txt"
    touch "$dir/file@with@at.txt"
    touch "$dir/file#with#hash.txt"
    touch "$dir/file\$with\$dollar.txt"

    # Create files with unicode characters (if supported)
    touch "$dir/файл_кириллица.txt" 2>/dev/null || true
    touch "$dir/文件_中文.txt" 2>/dev/null || true
    touch "$dir/ファイル_日本語.txt" 2>/dev/null || true

    log "Special character files created: $(ls -la "$dir" | wc -l) files"
}

# Generate files with various permissions
generate_permission_scenarios() {
    local dir="$TEST_DATA_DIR/permissions"
    log "Generating files with various permissions in $dir"
    mkdir -p "$dir"

    # Regular file
    echo "Regular file" > "$dir/regular_644.txt"
    chmod 644 "$dir/regular_644.txt"

    # Read-only file
    echo "Read-only file" > "$dir/readonly_444.txt"
    chmod 444 "$dir/readonly_444.txt"

    # Executable file
    echo "#!/bin/bash\necho 'Executable'" > "$dir/executable_755.sh"
    chmod 755 "$dir/executable_755.sh"

    # No read permission (may cause issues)
    echo "No read" > "$dir/noread_200.txt"
    chmod 200 "$dir/noread_200.txt" || warn "Could not set 200 permissions"

    # Owner only
    echo "Owner only" > "$dir/owner_600.txt"
    chmod 600 "$dir/owner_600.txt"

    # Group writable
    echo "Group writable" > "$dir/group_664.txt"
    chmod 664 "$dir/group_664.txt"

    log "Permission scenarios created: $(ls -la "$dir" | wc -l) files"
}

# Generate symlinks and hard links
generate_links() {
    local dir="$TEST_DATA_DIR/links"
    log "Generating symlinks and hard links in $dir"
    mkdir -p "$dir"

    # Create original files
    echo "Original file 1" > "$dir/original1.txt"
    echo "Original file 2" > "$dir/original2.txt"

    # Create symlinks
    ln -s original1.txt "$dir/symlink1.txt"
    ln -s original2.txt "$dir/symlink2.txt"

    # Create hard links
    ln "$dir/original1.txt" "$dir/hardlink1.txt"
    ln "$dir/original2.txt" "$dir/hardlink2.txt"

    # Create broken symlink
    ln -s nonexistent.txt "$dir/broken_symlink.txt"

    # Create directory symlink
    mkdir -p "$dir/target_dir"
    echo "Target content" > "$dir/target_dir/file.txt"
    ln -s target_dir "$dir/dir_symlink"

    log "Links created: $(find "$dir" -type l | wc -l) symlinks, $(find "$dir" -type f -links +1 | wc -l) hard links"
}

# Generate binary and text files
generate_mixed_content() {
    local dir="$TEST_DATA_DIR/mixed_content"
    log "Generating mixed content (binary and text) in $dir"
    mkdir -p "$dir"

    # Text files
    echo "Plain text content" > "$dir/plain.txt"
    echo -e "Line 1\nLine 2\nLine 3" > "$dir/multiline.txt"

    # Binary files
    dd if=/dev/urandom of="$dir/random.bin" bs=1K count=100 2>/dev/null

    # Empty file
    touch "$dir/empty.txt"

    # Large text file
    for i in {1..10000}; do
        echo "This is line $i of a large text file" >> "$dir/large_text.txt"
    done

    log "Mixed content created: $(ls -la "$dir" | wc -l) files"
}

# Simulate file modifications over time
generate_modified_files() {
    local dir="$TEST_DATA_DIR/modified_files"
    log "Generating files with modification times in $dir"
    mkdir -p "$dir"

    # Create files with different timestamps
    for i in {1..10}; do
        echo "Version $i" > "$dir/versioned_file.txt"
        touch -d "$(date -d "$i days ago" '+%Y-%m-%d %H:%M:%S')" "$dir/file_${i}_days_ago.txt" 2>/dev/null || \
        touch -t "$(date -v-${i}d '+%Y%m%d%H%M.%S')" "$dir/file_${i}_days_ago.txt" 2>/dev/null || \
        touch "$dir/file_${i}_days_ago.txt"
    done

    log "Modified files created: $(ls -la "$dir" | wc -l) files"
}

# Generate realistic directory structure
generate_realistic_structure() {
    local dir="$TEST_DATA_DIR/realistic"
    log "Generating realistic directory structure in $dir"
    mkdir -p "$dir"

    # Simulate a small project structure
    mkdir -p "$dir/src/main/java/com/example/app"
    mkdir -p "$dir/src/main/resources"
    mkdir -p "$dir/src/test/java/com/example/app"
    mkdir -p "$dir/build/classes"
    mkdir -p "$dir/docs"
    mkdir -p "$dir/config"

    # Create some files
    echo "package com.example.app;" > "$dir/src/main/java/com/example/app/Main.java"
    echo "public class Main {}" >> "$dir/src/main/java/com/example/app/Main.java"

    echo "# Configuration" > "$dir/config/app.conf"
    echo "# README" > "$dir/README.md"

    for i in {1..20}; do
        echo "Class$i" > "$dir/src/main/java/com/example/app/Class$i.java"
    done

    log "Realistic structure created"
}

# Main execution
main() {
    log "Starting test data generation..."
    log "Configuration: TEST_DATA_DIR=$TEST_DATA_DIR, LARGE_FILE_SIZE=$LARGE_FILE_SIZE, HIGH_FILE_COUNT=$HIGH_FILE_COUNT"

    create_base_structure
    generate_large_files
    generate_high_file_count
    generate_deep_nesting
    generate_special_chars
    generate_permission_scenarios
    generate_links
    generate_mixed_content
    generate_modified_files
    generate_realistic_structure

    log "Test data generation complete!"
    log "Total size: $(du -sh "$TEST_DATA_DIR" | cut -f1)"
    log "Total files: $(find "$TEST_DATA_DIR" -type f | wc -l)"
    log "Total directories: $(find "$TEST_DATA_DIR" -type d | wc -l)"
}

# Run main function
main "$@"
