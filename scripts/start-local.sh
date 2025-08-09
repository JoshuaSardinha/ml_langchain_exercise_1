#!/bin/bash

# Data Doctor - Stop Local Development Services
# Companion script to stop all services started by start-local-new.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

print_info "Stopping Data Doctor services..."

# Stop services using PID files
if [ -f "logs/ml-service.pid" ]; then
    ML_PID=$(cat logs/ml-service.pid)
    if kill -0 $ML_PID 2>/dev/null; then
        print_info "Stopping ML Service (PID: $ML_PID)..."
        kill $ML_PID
        rm logs/ml-service.pid
    else
        print_info "ML Service was not running"
        rm logs/ml-service.pid 2>/dev/null || true
    fi
fi

if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        print_info "Stopping Backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        rm logs/backend.pid
    else
        print_info "Backend was not running"
        rm logs/backend.pid 2>/dev/null || true
    fi
fi

if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        print_info "Stopping Frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        rm logs/frontend.pid
    else
        print_info "Frontend was not running"
        rm logs/frontend.pid 2>/dev/null || true
    fi
fi

# Fallback: kill any processes on our ports
print_info "Cleaning up any remaining processes on ports 8000, 3000, 4200..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true  
lsof -ti:4200 | xargs kill -9 2>/dev/null || true

# Stop NX daemon
print_info "Stopping NX daemon..."
npx nx daemon --stop 2>/dev/null || true

sleep 2

print_success "✅ All services stopped"
print_info "Logs are preserved in the logs/ directory"