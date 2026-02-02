#!/bin/bash
###############################################################################
# SurfScreen Comprehensive Test Suite - Main Orchestrator
# 
# Usage: ./run_all_tests.sh [options]
# Options:
#   --skip-gpu      GPU 테스트 스킵
#   --skip-api      API 테스트 스킵
#   --parallel N    병렬 워커 수 (기본: 자동 감지)
#   --quick         빠른 테스트만 실행
#   --verbose       상세 출력
#
# Environment:
#   - Linux cluster with 36 CPUs and L4 GPU
#   - Python 3.9+
#   - CUDA support for GPU tests
###############################################################################

set -euo pipefail

# ============================================
# Configuration
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/tests"
LOG_DIR="$PROJECT_ROOT/test_outputs"
DATE_TAG=$(date +"%Y%m%d_%H%M%S")
MAIN_LOG="$LOG_DIR/test_run_${DATE_TAG}.log"
SUMMARY_LOG="$LOG_DIR/test_summary_${DATE_TAG}.log"
FAILED_LOG="$LOG_DIR/test_failed_${DATE_TAG}.log"

# Default options
SKIP_GPU=false
SKIP_API=false
PARALLEL_WORKERS=$(nproc 2>/dev/null || echo 8)
QUICK_MODE=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================
# Parse Arguments
# ============================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-gpu)
            SKIP_GPU=true
            shift
            ;;
        --skip-api)
            SKIP_API=true
            shift
            ;;
        --parallel)
            PARALLEL_WORKERS="$2"
            shift 2
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================
# Helper Functions
# ============================================
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "[$timestamp] [$level] $message" | tee -a "$MAIN_LOG"
}

log_info() { log "INFO" "$1"; }
log_warn() { log "WARN" "${YELLOW}$1${NC}"; }
log_error() { log "ERROR" "${RED}$1${NC}"; }
log_success() { log "SUCCESS" "${GREEN}$1${NC}"; }

section_header() {
    local title="$1"
    echo "" | tee -a "$MAIN_LOG"
    echo "============================================" | tee -a "$MAIN_LOG"
    echo -e "${CYAN}$title${NC}" | tee -a "$MAIN_LOG"
    echo "============================================" | tee -a "$MAIN_LOG"
}

run_test_script() {
    local script_name="$1"
    local script_path="$SCRIPT_DIR/$script_name"
    local test_log="$LOG_DIR/${script_name%.sh}_${DATE_TAG}.log"
    
    if [[ ! -f "$script_path" ]]; then
        log_error "Script not found: $script_path"
        return 1
    fi
    
    log_info "Running $script_name..."
    
    local start_time=$(date +%s)
    local exit_code=0
    
    if [[ "$VERBOSE" == "true" ]]; then
        bash "$script_path" 2>&1 | tee -a "$test_log" || exit_code=$?
    else
        bash "$script_path" > "$test_log" 2>&1 || exit_code=$?
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "$script_name completed in ${duration}s"
        echo "PASS: $script_name (${duration}s)" >> "$SUMMARY_LOG"
    else
        log_error "$script_name failed (exit code: $exit_code) - see $test_log"
        echo "FAIL: $script_name (${duration}s) - exit code: $exit_code" >> "$SUMMARY_LOG"
        echo "$script_name: $test_log" >> "$FAILED_LOG"
    fi
    
    return $exit_code
}

# ============================================
# Setup
# ============================================
setup_environment() {
    section_header "Environment Setup"
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Initialize log files
    echo "SurfScreen Test Run - $DATE_TAG" > "$MAIN_LOG"
    echo "================================" >> "$MAIN_LOG"
    echo "" > "$SUMMARY_LOG"
    echo "Failed Tests:" > "$FAILED_LOG"
    
    # Log environment info
    log_info "Project Root: $PROJECT_ROOT"
    log_info "Test Directory: $TEST_DIR"
    log_info "Log Directory: $LOG_DIR"
    log_info "Parallel Workers: $PARALLEL_WORKERS"
    log_info "Quick Mode: $QUICK_MODE"
    log_info "Skip GPU: $SKIP_GPU"
    log_info "Skip API: $SKIP_API"
    
    # Check Python
    log_info "Python Version: $(python --version 2>&1)"
    
    # Check GPU availability
    if command -v nvidia-smi &> /dev/null; then
        log_info "GPU Info:"
        nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | tee -a "$MAIN_LOG"
    else
        log_warn "nvidia-smi not found - GPU tests may fail"
    fi
    
    # Check CUDA
    if python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')" 2>/dev/null; then
        python -c "import torch; print(f'CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')" | tee -a "$MAIN_LOG"
    fi
    
    # Activate virtual environment if exists
    if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
        log_info "Activating virtual environment..."
        source "$PROJECT_ROOT/.venv/bin/activate"
    fi
    
    # Install test dependencies
    log_info "Installing test dependencies..."
    pip install pytest pytest-cov pytest-asyncio pytest-xdist pytest-timeout httpx --quiet
    
    log_success "Environment setup complete"
}

# ============================================
# Main Test Execution
# ============================================
main() {
    local total_start=$(date +%s)
    local failed_count=0
    local passed_count=0
    local skipped_count=0
    
    setup_environment
    
    # ----------------------------------------
    # 1. Unit Tests
    # ----------------------------------------
    section_header "1. Unit Tests"
    if run_test_script "run_unit_tests.sh"; then
        ((passed_count++))
    else
        ((failed_count++))
    fi
    
    # ----------------------------------------
    # 2. Integration Tests
    # ----------------------------------------
    section_header "2. Integration Tests"
    if run_test_script "run_integration_tests.sh"; then
        ((passed_count++))
    else
        ((failed_count++))
    fi
    
    # ----------------------------------------
    # 3. API Tests
    # ----------------------------------------
    if [[ "$SKIP_API" == "false" ]]; then
        section_header "3. API Tests"
        if run_test_script "run_api_tests.sh"; then
            ((passed_count++))
        else
            ((failed_count++))
        fi
    else
        log_warn "Skipping API tests (--skip-api)"
        ((skipped_count++))
    fi
    
    # ----------------------------------------
    # 4. CLI Tests
    # ----------------------------------------
    section_header "4. CLI Tests"
    if run_test_script "run_cli_tests.sh"; then
        ((passed_count++))
    else
        ((failed_count++))
    fi
    
    # ----------------------------------------
    # 5. GPU/MACE Tests
    # ----------------------------------------
    if [[ "$SKIP_GPU" == "false" ]]; then
        section_header "5. GPU/MACE Tests"
        if run_test_script "run_gpu_tests.sh"; then
            ((passed_count++))
        else
            ((failed_count++))
        fi
    else
        log_warn "Skipping GPU tests (--skip-gpu)"
        ((skipped_count++))
    fi
    
    # ----------------------------------------
    # 6. E2E Workflow Tests
    # ----------------------------------------
    section_header "6. E2E Workflow Tests"
    if run_test_script "run_e2e_tests.sh"; then
        ((passed_count++))
    else
        ((failed_count++))
    fi
    
    # ----------------------------------------
    # 7. Performance Tests (unless quick mode)
    # ----------------------------------------
    if [[ "$QUICK_MODE" == "false" ]]; then
        section_header "7. Performance Tests"
        if run_test_script "run_performance_tests.sh"; then
            ((passed_count++))
        else
            ((failed_count++))
        fi
    else
        log_warn "Skipping performance tests (--quick)"
        ((skipped_count++))
    fi
    
    # ----------------------------------------
    # Generate Final Report
    # ----------------------------------------
    local total_end=$(date +%s)
    local total_duration=$((total_end - total_start))
    
    section_header "TEST EXECUTION COMPLETE"
    
    echo "" >> "$SUMMARY_LOG"
    echo "================================" >> "$SUMMARY_LOG"
    echo "FINAL SUMMARY" >> "$SUMMARY_LOG"
    echo "================================" >> "$SUMMARY_LOG"
    echo "Total Duration: ${total_duration}s" >> "$SUMMARY_LOG"
    echo "Passed: $passed_count" >> "$SUMMARY_LOG"
    echo "Failed: $failed_count" >> "$SUMMARY_LOG"
    echo "Skipped: $skipped_count" >> "$SUMMARY_LOG"
    
    log_info "Total Duration: ${total_duration}s"
    log_info "Passed: ${GREEN}$passed_count${NC}"
    log_info "Failed: ${RED}$failed_count${NC}"
    log_info "Skipped: ${YELLOW}$skipped_count${NC}"
    
    echo ""
    log_info "Log files:"
    log_info "  Main Log: $MAIN_LOG"
    log_info "  Summary: $SUMMARY_LOG"
    log_info "  Failed Tests: $FAILED_LOG"
    
    # Display failed tests
    if [[ $failed_count -gt 0 ]]; then
        echo ""
        log_error "=== FAILED TESTS ==="
        cat "$FAILED_LOG" | tee -a "$MAIN_LOG"
    fi
    
    # Exit with error if any tests failed
    if [[ $failed_count -gt 0 ]]; then
        exit 1
    fi
    
    log_success "All tests passed!"
    exit 0
}

# Run main
main "$@"
