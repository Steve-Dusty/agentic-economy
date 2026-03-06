#!/bin/bash

set -e

cd "$(dirname "$0")/../.."

# Read version from VERSION file
VERSION=$(cat VERSION 2>/dev/null || echo "latest")
VERSION=$(echo "$VERSION" | tr -d '[:space:]')

echo "====================================="
echo "Building Trinity Agent Base Image"
echo "Version: $VERSION"
echo "====================================="
echo ""

# Build with version tag and latest tag
docker build \
    -t trinity-agent-base:${VERSION} \
    -t trinity-agent-base:latest \
    --build-arg VERSION=${VERSION} \
    -f docker/base-image/Dockerfile docker/base-image/

echo ""
echo "✅ Base image built successfully:"
echo "   - trinity-agent-base:${VERSION}"
echo "   - trinity-agent-base:latest"
echo ""

