#!/bin/bash
# Test script for Cloud Run Python Executor

SERVICE_URL="${SERVICE_URL:-https://python-executor-256857162008.us-central1.run.app}"

echo "Testing service at: $SERVICE_URL"
echo "================================"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
curl -s $SERVICE_URL/health | jq .
echo ""

# Test 2: Simple Execution
echo "Test 2: Simple Execution"
curl -s -X POST $SERVICE_URL/execute \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n    print(\"Hello World\")\n    return {\"status\": \"success\", \"message\": \"Hello from sandbox!\"}"}' | jq .
echo ""

# Test 3: Math Operations
echo "Test 3: Math Operations"
curl -s -X POST $SERVICE_URL/execute \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n    result = sum(range(100))\n    return {\"sum\": result}"}' | jq .
echo ""

# Test 4: Libraries Test
echo "Test 4: Libraries Test (pandas/numpy)"
curl -s -X POST $SERVICE_URL/execute \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n    import pandas as pd\n    import numpy as np\n    return {\"pandas\": pd.__version__, \"numpy\": np.__version__}"}' | jq .
echo ""

# Test 5: Security Test
echo "Test 5: Security Test (file access)"
curl -s -X POST $SERVICE_URL/execute \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n    try:\n        with open(\"/etc/passwd\") as f:\n            return {\"pwned\": f.read()}\n    except Exception as e:\n        return {\"error\": str(e)}"}' | jq .
echo ""

# Test 6: Timeout Test
echo "Test 6: Timeout Test (should timeout)"
curl -s -X POST $SERVICE_URL/execute \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n    import time\n    time.sleep(10)\n    return {\"status\": \"should not reach here\"}"}' | jq .
echo ""

echo "================================"
echo "Tests complete!"
