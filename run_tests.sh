#!/bin/bash
# LightRAG Backend Test Runner
# This script runs all test suites and provides a comprehensive report

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Test categories
declare -A TEST_SUITES=(
    ["unit"]="tests/unit"
    ["integration"]="tests/integration"
    ["infrastructure"]="tests/infrastructure"
)

# Script configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Parse command line arguments
RUN_ALL=true
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_INFRASTRUCTURE=false
VERBOSE=false
COVERAGE=false
PARALLEL=false
HTML_REPORT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_ALL=false
            RUN_UNIT=true
            shift
            ;;
        --integration)
            RUN_ALL=false
            RUN_INTEGRATION=true
            shift
            ;;
        --infrastructure)
            RUN_ALL=false
            RUN_INFRASTRUCTURE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --html)
            HTML_REPORT=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --unit              Run only unit tests"
            echo "  --integration       Run only integration tests"
            echo "  --infrastructure    Run only infrastructure tests"
            echo "  --verbose, -v       Show verbose test output"
            echo "  --coverage, -c      Generate coverage report"
            echo "  --parallel, -p      Run tests in parallel"
            echo "  --html              Generate HTML test report"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "By default, all test suites are run."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to print section headers
print_header() {
    echo -e "\n${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Function to check service health
check_services() {
    print_header "🔍 Checking Service Health"
    
    local services_ok=true
    
    # Check Ollama
    echo -n "Checking Ollama... "
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not running${NC}"
        services_ok=false
    fi
    
    # Check Qdrant
    echo -n "Checking Qdrant... "
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not running${NC}"
        services_ok=false
    fi
    
    # Check Redis
    echo -n "Checking Redis... "
    # Try different methods to check Redis
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    elif nc -z localhost 6379 2>/dev/null; then
        echo -e "${GREEN}✓ Running (port 6379 open)${NC}"
    elif timeout 2 bash -c 'cat < /dev/null > /dev/tcp/localhost/6379' 2>/dev/null; then
        echo -e "${GREEN}✓ Running (port accessible)${NC}"
    else
        # Final check - see if docker container is running
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q rag_redis; then
            echo -e "${GREEN}✓ Running (docker container up)${NC}"
        else
            echo -e "${RED}✗ Not running${NC}"
            services_ok=false
        fi
    fi
    
    # Check Prometheus
    echo -n "Checking Prometheus... "
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not running${NC}"
        services_ok=false
    fi
    
    # Check Grafana
    echo -n "Checking Grafana... "
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${YELLOW}⚠ Not running (optional)${NC}"
    fi
    
    # Check API
    echo -n "Checking API... "
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${YELLOW}⚠ Not running (will start if needed)${NC}"
    fi
    
    if [ "$services_ok" = false ]; then
        echo -e "\n${RED}Some required services are not running!${NC}"
        echo "Please start Docker Compose services:"
        echo "  docker-compose up -d"
        exit 1
    fi
    
    echo -e "\n${GREEN}All required services are healthy!${NC}"
}

# Function to run a test suite
run_test_suite() {
    local suite_name=$1
    local suite_path=$2
    local pytest_args=""
    
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -v"
    else
        pytest_args="$pytest_args -q"
    fi
    
    if [ "$COVERAGE" = true ]; then
        pytest_args="$pytest_args --cov=src --cov-report=term-missing"
    fi
    
    if [ "$PARALLEL" = true ] && [ "$suite_name" != "infrastructure" ]; then
        # Don't run infrastructure tests in parallel as they may conflict
        pytest_args="$pytest_args -n auto"
    fi
    
    if [ "$HTML_REPORT" = true ]; then
        pytest_args="$pytest_args --html=test-reports/${suite_name}-report.html --self-contained-html"
    fi
    
    print_header "🧪 Running ${suite_name^} Tests"
    
    # Create test reports directory if HTML reports are enabled
    if [ "$HTML_REPORT" = true ]; then
        mkdir -p test-reports
    fi
    
    # Run the tests and capture output
    if [ "$VERBOSE" = true ]; then
        python -m pytest $suite_path $pytest_args
    else
        output=$(python -m pytest $suite_path $pytest_args --tb=short 2>&1)
        exit_code=$?
        
        # Parse test results
        if echo "$output" | grep -q "passed"; then
            passed=$(echo "$output" | grep -oP '\d+(?= passed)' | tail -1)
            PASSED_TESTS=$((PASSED_TESTS + passed))
        fi
        
        if echo "$output" | grep -q "failed"; then
            failed=$(echo "$output" | grep -oP '\d+(?= failed)' | tail -1)
            FAILED_TESTS=$((FAILED_TESTS + failed))
        fi
        
        if echo "$output" | grep -q "skipped"; then
            skipped=$(echo "$output" | grep -oP '\d+(?= skipped)' | tail -1)
            SKIPPED_TESTS=$((SKIPPED_TESTS + skipped))
        fi
        
        # Show summary
        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}✓ All ${suite_name} tests passed!${NC}"
        else
            echo -e "${RED}✗ Some ${suite_name} tests failed${NC}"
            echo "$output" | grep -E "(FAILED|ERROR)" | head -10
        fi
        
        return $exit_code
    fi
}

# Main execution
echo -e "${BOLD}${BLUE}🚀 LightRAG Backend Test Runner${NC}"
echo -e "${BLUE}================================${NC}\n"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not in a virtual environment${NC}"
    echo "Consider activating your virtual environment first"
fi

# Check services
check_services

# Install test dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "\n${YELLOW}Installing test dependencies...${NC}"
    pip install pytest pytest-asyncio pytest-cov pytest-xdist pytest-html
fi

# Run selected test suites
overall_exit_code=0

if [ "$RUN_ALL" = true ] || [ "$RUN_UNIT" = true ]; then
    run_test_suite "unit" "${TEST_SUITES[unit]}"
    [ $? -ne 0 ] && overall_exit_code=1
fi

if [ "$RUN_ALL" = true ] || [ "$RUN_INTEGRATION" = true ]; then
    run_test_suite "integration" "${TEST_SUITES[integration]}"
    [ $? -ne 0 ] && overall_exit_code=1
fi

if [ "$RUN_ALL" = true ] || [ "$RUN_INFRASTRUCTURE" = true ]; then
    run_test_suite "infrastructure" "${TEST_SUITES[infrastructure]}"
    [ $? -ne 0 ] && overall_exit_code=1
fi

# Calculate totals
TOTAL_TESTS=$((PASSED_TESTS + FAILED_TESTS))

# Print final summary
print_header "📊 Test Summary"

echo -e "${BOLD}Total Tests:${NC} $TOTAL_TESTS"
echo -e "${GREEN}Passed:${NC} $PASSED_TESTS"
echo -e "${RED}Failed:${NC} $FAILED_TESTS"

if [ $SKIPPED_TESTS -gt 0 ]; then
    echo -e "${YELLOW}Skipped:${NC} $SKIPPED_TESTS"
fi

if [ $TOTAL_TESTS -gt 0 ]; then
    success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo -e "\n${BOLD}Success Rate:${NC} ${success_rate}%"
    
    if [ $success_rate -ge 90 ]; then
        echo -e "${GREEN}✅ Excellent test coverage!${NC}"
    elif [ $success_rate -ge 70 ]; then
        echo -e "${YELLOW}⚠️  Good test coverage, but could be improved${NC}"
    else
        echo -e "${RED}❌ Poor test coverage, needs attention${NC}"
    fi
fi

# Coverage report location
if [ "$COVERAGE" = true ]; then
    echo -e "\n${BOLD}Coverage Report:${NC}"
    echo "Terminal report shown above"
    echo "HTML report: htmlcov/index.html"
fi

# HTML report location
if [ "$HTML_REPORT" = true ]; then
    echo -e "\n${BOLD}HTML Test Reports:${NC}"
    echo "Reports saved in: test-reports/"
fi

# Exit with appropriate code
exit $overall_exit_code