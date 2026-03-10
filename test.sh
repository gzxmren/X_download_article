#!/bin/bash

# Enhanced test runner with flexible arguments
# Usage:
#   ./test.sh               # Run all tests with coverage
#   ./test.sh tests/unit    # Run only unit tests
#   ./test.sh -k test_name  # Run tests matching pattern

# Ensure we're in the project root
cd "$(dirname "$0")"

# Execute pytest with passed arguments or default to all tests
if [ $# -eq 0 ]; then
    echo "Running all tests with default coverage settings..."
    python3 -m pytest
else
    echo "Running tests with custom arguments: $@"
    python3 -m pytest "$@"
fi

# Print instructions for HTML coverage report
if [ -d "htmlcov" ]; then
    echo ""
    echo "📊 Coverage report generated in htmlcov/index.html"
fi
