#!/bin/bash
set -e

echo "🐍 Python Executor - Local Setup Script"
echo "--------------------------------------"

# 1. Build the Docker image
echo "📦 Building docker image..."
docker build -t python-executor .

# 2. Stop any existing container on port 8080
echo "🛑 Checking for existing containers on port 8080..."
EXISTING=$(docker ps -q --filter "publish=8080")
if [ ! -z "$EXISTING" ]; then
    echo "⚠️  Stopping existing container..."
    docker stop $EXISTING
fi

# 3. Run container with required privileges
echo "🚀 Running container with nsjail enabled..."
docker run --rm -p 8080:8080 --privileged python-executor

echo "🎉 Local environment ready!"
echo "Send a test request:"
echo "curl -X POST -H \"Content-Type: application/json\" -d '{\"script\": \"def main(): return {\\\"ok\\\": True}\"}' http://localhost:8080/execute"