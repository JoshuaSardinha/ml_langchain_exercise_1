#!/bin/bash

# Data Doctor - Stop Local Development Services
# Companion script to stop all services started by start-local.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Status indicators
INFO_ICON="ℹ️"
SUCCESS_ICON="✅"
ERROR_ICON="❌"
WARNING_ICON="⚠️"

print_info() { echo -e "${CYAN}${INFO_ICON} [INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}${SUCCESS_ICON} [SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}${ERROR_ICON} [ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}${WARNING_ICON} [WARNING]${NC} $1"; }

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Service configuration
ML_SERVICE_PORT=8000
BACKEND_PORT=3000
FRONTEND_PORT=4200

main() {
    echo ""
    echo "=========================================="
    echo "🛑 Data Doctor - Stopping Local Services"
    echo "=========================================="
    echo ""
    
    cd "$PROJECT_ROOT"
    
    print_info "Stopping Data Doctor services..."
    
    local services_stopped=0
    
    # Stop services using PID files
    for service in ml-service backend frontend; do
        if [ -f "logs/${service}.pid" ]; then
            local pid=$(cat "logs/${service}.pid")
            if kill -0 "$pid" 2>/dev/null; then
                print_info "Stopping $service (PID: $pid)..."
                kill "$pid"
                sleep 2
                
                # Force kill if still running
                if kill -0 "$pid" 2>/dev/null; then
                    print_warning "Force stopping $service..."
                    kill -9 "$pid" 2>/dev/null || true
                fi
                
                services_stopped=$((services_stopped + 1))
                print_success "$service stopped"
            else
                print_info "$service was not running"
            fi
            rm -f "logs/${service}.pid"
        else
            print_info "No PID file found for $service"
        fi
    done
    
    # Fallback: kill any processes on our ports
    print_info "Cleaning up any remaining processes on service ports..."
    for port in $ML_SERVICE_PORT $BACKEND_PORT $FRONTEND_PORT; do
        local pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            print_warning "Found processes still using port $port, stopping them..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
            services_stopped=$((services_stopped + 1))
        fi
    done
    
    # Stop NX daemon
    print_info "Stopping NX daemon..."
    npx nx daemon --stop 2>/dev/null || true
    
    sleep 1
    
    echo ""
    if [ $services_stopped -gt 0 ]; then
        print_success "✅ Successfully stopped $services_stopped service(s)"
    else
        print_info "No services were running"
    fi
    
    print_info "📋 Logs are preserved in the logs/ directory"
    print_info "🚀 Use scripts/start-local.sh to start services again"
    echo ""
}

# Run main function
main "$@"