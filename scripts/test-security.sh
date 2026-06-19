#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "  🔒 SECURITY TEST SUITE"
echo "  Testing Network Isolation"
echo -e "==========================================${NC}"
echo ""

# Test 1: Database not accessible from public
echo -e "${YELLOW}Test 1: Database external access${NC}"
echo -n "  Attempting to connect to database... "
docker run --rm --network web_network alpine sh -c "timeout 3 nc -zv database 5432" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${RED}❌ FAIL: Database IS accessible externally!${NC}"
    exit 1
else
    echo -e "${GREEN}✅ PASS: Database is NOT accessible externally${NC}"
fi

# Test 2: Cache not accessible from public
echo -e "\n${YELLOW}Test 2: Cache external access${NC}"
echo -n "  Attempting to connect to cache... "
docker run --rm --network web_network alpine sh -c "timeout 3 nc -zv cache 6379" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${RED}❌ FAIL: Cache IS accessible externally!${NC}"
    exit 1
else
    echo -e "${GREEN}✅ PASS: Cache is NOT accessible externally${NC}"
fi

# Test 3: Worker can access database
echo -e "\n${YELLOW}Test 3: Worker to database communication${NC}"
echo -n "  Worker connecting to database... "
docker exec worker_service sh -c "nc -zv database 5432" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASS: Worker can access database${NC}"
else
    echo -e "${RED}❌ FAIL: Worker cannot access database${NC}"
    exit 1
fi

# Test 4: Worker can access cache
echo -e "\n${YELLOW}Test 4: Worker to cache communication${NC}"
echo -n "  Worker connecting to cache... "
docker exec worker_service sh -c "nc -zv cache 6379" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASS: Worker can access cache${NC}"
else
    echo -e "${RED}❌ FAIL: Worker cannot access cache${NC}"
    exit 1
fi

# Test 5: Internal network has no internet
echo -e "\n${YELLOW}Test 5: Internal network internet access${NC}"
echo -n "  Internal network accessing internet... "
docker run --rm --network secure_network alpine sh -c "timeout 3 ping -c 1 8.8.8.8" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${RED}❌ FAIL: Internal network CAN access internet!${NC}"
    exit 1
else
    echo -e "${GREEN}✅ PASS: Internal network has NO internet access${NC}"
fi

echo -e "\n${GREEN}=========================================="
echo "  ✅ ALL SECURITY TESTS PASSED!"
echo "  Your services are properly isolated."
echo -e "==========================================${NC}"
