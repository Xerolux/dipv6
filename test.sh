#!/bin/bash

###############################################################################
# Test script for Dynamic IPv6/IPv4 DDNS Service
# Tests all components of the installation
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SERVICE_NAME="dynipv6"
SERVICE_PORT="5000"
CONFIG_FILE="/etc/dynipv6/config.json"
LOG_FILE="/var/log/dynipv6/dynipv6.log"

echo -e "${BLUE}=== Dynamic IPv6/IPv4 DDNS Service - Test Suite ===${NC}"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

###############################################################################
# System Checks
###############################################################################

echo -e "${YELLOW}=== System Checks ===${NC}"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    test_result 0 "Running as root"
else
    test_result 1 "Not running as root (some tests require root)"
fi

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" == "ubuntu" || "$ID" == "debian" ]]; then
        test_result 0 "Running on $ID $VERSION"
    else
        test_result 1 "Not running on Ubuntu/Debian"
    fi
else
    test_result 1 "Cannot determine OS"
fi

echo ""

###############################################################################
# Python Environment
###############################################################################

echo -e "${YELLOW}=== Python Environment ===${NC}"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    test_result 0 "Python 3 installed: $PYTHON_VERSION"
else
    test_result 1 "Python 3 not found"
fi

# Check required packages
PACKAGES=("flask" "flask_cors" "requests")
for PACKAGE in "${PACKAGES[@]}"; do
    if python3 -c "import ${PACKAGE//-/_}" 2>/dev/null; then
        test_result 0 "Python package '$PACKAGE' installed"
    else
        test_result 1 "Python package '$PACKAGE' not installed"
    fi
done

echo ""

###############################################################################
# Service Status
###############################################################################

echo -e "${YELLOW}=== Service Status ===${NC}"

# Check if service exists
if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    test_result 0 "Service unit file exists"
else
    test_result 1 "Service unit file not found"
fi

# Check if service is running
if systemctl is-active --quiet $SERVICE_NAME; then
    test_result 0 "Service is running"
else
    test_result 1 "Service is not running"
fi

# Check if service is enabled
if systemctl is-enabled --quiet $SERVICE_NAME; then
    test_result 0 "Service is enabled for auto-start"
else
    test_result 1 "Service is not enabled for auto-start"
fi

echo ""

###############################################################################
# Configuration
###############################################################################

echo -e "${YELLOW}=== Configuration ===${NC}"

# Check if config file exists
if [ -f "$CONFIG_FILE" ]; then
    test_result 0 "Configuration file exists"

    # Check config file permissions
    PERMS=$(stat -c "%a" "$CONFIG_FILE")
    if [ "$PERMS" == "644" ] || [ "$PERMS" == "600" ]; then
        test_result 0 "Configuration file permissions are secure ($PERMS)"
    else
        test_result 1 "Configuration file permissions may be too open ($PERMS)"
    fi

    # Check if required fields exist
    if grep -q "ipv6_domain" "$CONFIG_FILE"; then
        test_result 0 "ipv6_domain configured"
    else
        test_result 1 "ipv6_domain not configured"
    fi

    if grep -q "ipv4_domain" "$CONFIG_FILE"; then
        test_result 0 "ipv4_domain configured"
    else
        test_result 1 "ipv4_domain not configured"
    fi

    if grep -q "auth_tokens" "$CONFIG_FILE"; then
        test_result 0 "auth_tokens configured"
    else
        test_result 1 "auth_tokens not configured"
    fi
else
    test_result 1 "Configuration file not found"
fi

echo ""

###############################################################################
# Directory Structure
###############################################################################

echo -e "${YELLOW}=== Directory Structure ===${NC}"

# Check directories
DIRS=(
    "/opt/dynipv6"
    "/etc/dynipv6"
    "/var/lib/dynipv6"
    "/var/log/dynipv6"
)

for DIR in "${DIRS[@]}"; do
    if [ -d "$DIR" ]; then
        test_result 0 "Directory exists: $DIR"
    else
        test_result 1 "Directory missing: $DIR"
    fi
done

echo ""

###############################################################################
# File Checks
###############################################################################

echo -e "${YELLOW}=== Required Files ===${NC}"

FILES=(
    "/opt/dynipv6/dynipv6_service.py"
    "/etc/systemd/system/dynipv6.service"
    "$LOG_FILE"
)

for FILE in "${FILES[@]}"; do
    if [ -f "$FILE" ]; then
        test_result 0 "File exists: $FILE"
    else
        test_result 1 "File missing: $FILE"
    fi
done

echo ""

###############################################################################
# API Connectivity
###############################################################################

echo -e "${YELLOW}=== API Connectivity ===${NC}"

# Check if service is listening
if netstat -tuln 2>/dev/null | grep -q ":$SERVICE_PORT" || ss -tuln 2>/dev/null | grep -q ":$SERVICE_PORT"; then
    test_result 0 "Service listening on port $SERVICE_PORT"
else
    test_result 1 "Service not listening on port $SERVICE_PORT"
fi

# Test health endpoint
if command -v curl &> /dev/null; then
    if curl -s http://127.0.0.1:$SERVICE_PORT/api/health > /dev/null 2>&1; then
        test_result 0 "API health endpoint responding"
    else
        test_result 1 "API health endpoint not responding"
    fi
else
    echo -e "${YELLOW}⊘ SKIP${NC}: curl not available (install curl to test API)"
fi

echo ""

###############################################################################
# SSL/TLS
###############################################################################

echo -e "${YELLOW}=== SSL/TLS Configuration ===${NC}"

# Check for Let's Encrypt certificates
if [ -f "/etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem" ]; then
    test_result 0 "Let's Encrypt certificate for ipv6.xerolux.net exists"

    # Check expiration
    if command -v openssl &> /dev/null; then
        EXPIRY=$(openssl x509 -in /etc/letsencrypt/live/ipv6.xerolux.net/fullchain.pem -noout -enddate | cut -d= -f2)
        echo -e "  Certificate expiry: $EXPIRY"
    fi
else
    test_result 1 "Let's Encrypt certificate for ipv6.xerolux.net not found"
fi

if [ -f "/etc/letsencrypt/live/ipv4.xerolux.net/fullchain.pem" ]; then
    test_result 0 "Let's Encrypt certificate for ipv4.xerolux.net exists"
else
    test_result 1 "Let's Encrypt certificate for ipv4.xerolux.net not found"
fi

echo ""

###############################################################################
# Reverse Proxy
###############################################################################

echo -e "${YELLOW}=== Reverse Proxy Configuration ===${NC}"

# Check Nginx
if command -v nginx &> /dev/null; then
    if systemctl is-active --quiet nginx; then
        test_result 0 "Nginx is installed and running"
    else
        test_result 1 "Nginx is installed but not running"
    fi
else
    test_result 1 "Nginx not found (or Apache should be configured)"
fi

# Check Apache
if command -v apache2ctl &> /dev/null; then
    if systemctl is-active --quiet apache2; then
        test_result 0 "Apache is installed and running"
    else
        test_result 1 "Apache is installed but not running"
    fi
fi

echo ""

###############################################################################
# Logs
###############################################################################

echo -e "${YELLOW}=== Recent Logs ===${NC}"

if [ -f "$LOG_FILE" ]; then
    echo "Last 5 log entries:"
    tail -5 "$LOG_FILE" | sed 's/^/  /'
    echo ""
else
    echo -e "${YELLOW}⊘ SKIP${NC}: Log file not found"
fi

echo ""

###############################################################################
# Summary
###############################################################################

echo -e "${YELLOW}=== Test Summary ===${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
PERCENTAGE=$((TESTS_PASSED * 100 / TOTAL))

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo "Tests: $TESTS_PASSED/$TOTAL (100%)"
    exit 0
else
    echo -e "${YELLOW}Some tests failed:${NC}"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo "Total:  $TOTAL ($PERCENTAGE%)"
    echo ""
    echo -e "${YELLOW}Recommendations:${NC}"
    echo "1. Check logs: journalctl -u dynipv6 -f"
    echo "2. Review config: nano /etc/dynipv6/config.json"
    echo "3. Verify directories exist and have correct permissions"
    echo "4. Ensure SSL certificates are in place"
    exit 1
fi
