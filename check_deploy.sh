#!/bin/bash
# Pre-deployment checklist script

echo "🔍 Cloud Run Deployment Pre-flight Check"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

checks_passed=0
checks_failed=0

# Check 1: Procfile exists
echo -n "1. Checking Procfile... "
if [ -f "Procfile" ]; then
    echo -e "${GREEN}✓${NC}"
    ((checks_passed++))
else
    echo -e "${RED}✗${NC} Missing!"
    ((checks_failed++))
fi

# Check 2: requirements.txt exists
echo -n "2. Checking requirements.txt... "
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓${NC}"
    ((checks_passed++))
else
    echo -e "${RED}✗${NC} Missing!"
    ((checks_failed++))
fi

# Check 3: No problematic -e git line in requirements.txt
echo -n "3. Checking requirements.txt for -e git lines... "
if grep -q "^-e git+" requirements.txt; then
    echo -e "${RED}✗${NC} Found problematic line!"
    echo "   Fix: Remove the '-e git+...' line from requirements.txt"
    ((checks_failed++))
else
    echo -e "${GREEN}✓${NC}"
    ((checks_passed++))
fi

# Check 4: run.sh exists and is executable
echo -n "4. Checking run.sh... "
if [ -f "run.sh" ] && [ -x "run.sh" ]; then
    echo -e "${GREEN}✓${NC}"
    ((checks_passed++))
elif [ -f "run.sh" ]; then
    echo -e "${YELLOW}⚠${NC}  Exists but not executable"
    echo "   Run: chmod +x run.sh"
    ((checks_failed++))
else
    echo -e "${RED}✗${NC} Missing!"
    ((checks_failed++))
fi

# Check 5: gcloud CLI installed
echo -n "5. Checking gcloud CLI... "
if command -v gcloud &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
    ((checks_passed++))
else
    echo -e "${RED}✗${NC} Not installed!"
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    ((checks_failed++))
fi

# Check 6: gcloud authenticated
echo -n "6. Checking gcloud authentication... "
if gcloud auth list 2>&1 | grep -q "ACTIVE"; then
    echo -e "${GREEN}✓${NC}"
    ((checks_passed++))
else
    echo -e "${RED}✗${NC} Not authenticated!"
    echo "   Run: gcloud auth login"
    ((checks_failed++))
fi

# Check 7: gcloud project set
echo -n "7. Checking gcloud project... "
project=$(gcloud config get-value project 2>/dev/null)
if [ -n "$project" ] && [ "$project" != "(unset)" ]; then
    echo -e "${GREEN}✓${NC} ($project)"
    ((checks_passed++))
else
    echo -e "${RED}✗${NC} No project set!"
    echo "   Run: gcloud config set project YOUR_PROJECT_ID"
    ((checks_failed++))
fi

# Check 8: OPENAI_API_KEY set
echo -n "8. Checking OPENAI_API_KEY... "
if [ -n "$OPENAI_API_KEY" ]; then
    echo -e "${GREEN}✓${NC} (Set in environment)"
    ((checks_passed++))
else
    echo -e "${YELLOW}⚠${NC}  Not set in environment"
    echo "   You'll need to pass it in the deploy command with --set-env-vars"
    # Don't count as failure since it can be passed in deploy command
fi

echo ""
echo "========================================"
echo "Summary: ${GREEN}${checks_passed} passed${NC}, ${RED}${checks_failed} failed${NC}"
echo ""

if [ $checks_failed -eq 0 ]; then
    echo -e "${GREEN}✓ Ready to deploy!${NC}"
    echo ""
    echo "Run this command to deploy:"
    echo ""
    echo "gcloud run deploy appworld-green-agent \\"
    echo "  --source . \\"
    echo "  --region us-central1 \\"
    echo "  --allow-unauthenticated \\"
    echo "  --memory 2Gi \\"
    echo "  --cpu 2 \\"
    echo "  --timeout 300 \\"
    echo "  --set-env-vars OPENAI_API_KEY=your-key"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Please fix the issues above before deploying.${NC}"
    echo ""
    exit 1
fi


