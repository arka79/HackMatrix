#!/bin/bash

# ==========================================
# CI DOCTOR - HACKATHON DEMO SCRIPT
# ==========================================

set -u

LOG_DIR="reports"
LOG_FILE="$LOG_DIR/demo-output.log"

mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

run_step() {
    echo ""
    echo "=========================================="
    echo "RUNNING: $*"
    echo "=========================================="

    echo "" >> "$LOG_FILE"
    echo "==========================================" >> "$LOG_FILE"
    echo "RUNNING: $*" >> "$LOG_FILE"
    echo "==========================================" >> "$LOG_FILE"

    "$@" 2>&1 | tee -a "$LOG_FILE"
    status=${PIPESTATUS[0]}

    if [ "$status" -eq 0 ]; then
        echo "SUCCESS"
    else
        echo "Command exited with code $status"
    fi
}

echo "CI DOCTOR - LIVE DEMONSTRATION"
echo "Project: HackMatrix"
echo "Date: $(date)"

# 1. Check CLI
run_step uv run python -m cidoctor --help

# 2. Initialize CI Doctor
run_step uv run python -m cidoctor init

# 3. Analyze local JUnit results
if [ -f "results.xml" ]; then
    run_step uv run python -m cidoctor analyze results.xml
else
    echo "Skipping results.xml: file not found."
fi

# 4. Display recent GitHub Actions runs
run_step gh run list --limit 5

# 5. Analyze downloaded GitHub Actions JUnit report
if [ -f ".cidoctor/input/junit/junit.xml" ]; then
    run_step uv run python -m cidoctor analyze .cidoctor/input/junit/junit.xml
else
    echo "Skipping downloaded JUnit report: file not found."
fi

# 6. Historical flaky-test analysis
run_step uv run python -m cidoctor flaky

# 7. Gemini investigation
echo ""
echo "IMPORTANT: The explain command uses stored analysis data."
echo "Check the selected run before presenting its diagnosis."
run_step uv run python -m cidoctor explain

echo ""
echo "=========================================="
echo "DEMONSTRATION COMPLETED"
echo "=========================================="

echo "Output saved to: $LOG_FILE"
