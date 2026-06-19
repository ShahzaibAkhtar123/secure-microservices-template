#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "  🧪 API TEST SUITE"
echo "  Testing All Endpoints"
echo -e "==========================================${NC}"
echo ""

BASE_URL="http://localhost:8080"

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
HEALTH=$(curl -s ${BASE_URL}/health)
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo -e "  ${GREEN}✅ Health check passed${NC}"
else
    echo -e "  ${RED}❌ Health check failed${NC}"
    exit 1
fi

# Test 2: Create User
echo -e "\n${YELLOW}Test 2: Create User${NC}"
USER_DATA='{"username":"testuser","email":"test@example.com"}'
CREATE_RESULT=$(curl -s -X POST ${BASE_URL}/api/users \
    -H "Content-Type: application/json" \
    -d "$USER_DATA")
    
if echo "$CREATE_RESULT" | grep -q '"success":true'; then
    echo -e "  ${GREEN}✅ User created successfully${NC}"
    USER_ID=$(echo "$CREATE_RESULT" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    echo "  User ID: $USER_ID"
else
    echo -e "  ${RED}❌ User creation failed${NC}"
    exit 1
fi

# Test 3: Get User (test cache)
echo -e "\n${YELLOW}Test 3: Get User (Cache Test)${NC}"
GET_RESULT=$(curl -s ${BASE_URL}/api/users/${USER_ID})
if echo "$GET_RESULT" | grep -q '"success":true'; then
    echo -e "  ${GREEN}✅ User retrieved${NC}"
    if echo "$GET_RESULT" | grep -q '"from_cache":true'; then
        echo "  (Retrieved from cache)"
    else
        echo "  (Retrieved from database)"
    fi
else
    echo -e "  ${RED}❌ Failed to get user${NC}"
    exit 1
fi

# Test 4: Get All Users
echo -e "\n${YELLOW}Test 4: Get All Users${NC}"
LIST_RESULT=$(curl -s ${BASE_URL}/api/users)
if echo "$LIST_RESULT" | grep -q '"success":true'; then
    echo -e "  ${GREEN}✅ Users list retrieved${NC}"
else
    echo -e "  ${RED}❌ Failed to get users list${NC}"
    exit 1
fi

# Test 5: Delete User
echo -e "\n${YELLOW}Test 5: Delete User${NC}"
DELETE_RESULT=$(curl -s -X DELETE ${BASE_URL}/api/users/${USER_ID})
if echo "$DELETE_RESULT" | grep -q '"success":true'; then
    echo -e "  ${GREEN}✅ User deleted successfully${NC}"
else
    echo -e "  ${RED}❌ User deletion failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}=========================================="
echo "  ✅ ALL API TESTS PASSED!"
echo "  Your API is working correctly."
echo -e "==========================================${NC}"
