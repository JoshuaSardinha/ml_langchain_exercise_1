#!/bin/bash

# Data Doctor - Local Development Services Startup Script
# Starts ML Service, Backend, and Frontend with proper dependency management

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Status indicators
INFO_ICON="ℹ️"
SUCCESS_ICON="✅"
ERROR_ICON="❌"
WARNING_ICON="⚠️"
ROCKET_ICON="🚀"
LOADING_ICON="⏳"

print_info() { echo -e "${CYAN}${INFO_ICON} [INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}${SUCCESS_ICON} [SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}${ERROR_ICON} [ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}${WARNING_ICON} [WARNING]${NC} $1"; }
print_step() { echo -e "${PURPLE}${ROCKET_ICON} [STEP]${NC} $1"; }
print_loading() { echo -e "${BLUE}${LOADING_ICON} [LOADING]${NC} $1"; }

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Service configuration
ML_SERVICE_PORT=8000
BACKEND_PORT=3000
FRONTEND_PORT=4200

# Timeout configurations (in seconds)
SERVICE_START_TIMEOUT=60
HEALTH_CHECK_TIMEOUT=30
DEPENDENCY_INSTALL_TIMEOUT=300

# Cleanup function for graceful exit
cleanup_on_exit() {
    print_info "Cleaning up background processes..."
    
    # Kill services using PID files
    for service in ml-service backend frontend; do
        if [ -f "logs/${service}.pid" ]; then
            local pid=$(cat "logs/${service}.pid")
            if kill -0 "$pid" 2>/dev/null; then
                print_info "Stopping $service (PID: $pid)..."
                kill "$pid"
            fi
            rm -f "logs/${service}.pid"
        fi
    done
    
    # Kill any remaining processes on our ports
    for port in $ML_SERVICE_PORT $BACKEND_PORT $FRONTEND_PORT; do
        local pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            print_info "Cleaning up remaining processes on port $port..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
        fi
    done
    
    # Stop NX daemon
    npx nx daemon --stop 2>/dev/null || true
    
    print_info "Cleanup completed"
}

# Set up trap for cleanup
trap cleanup_on_exit EXIT INT TERM

# Prerequisites checking functions
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed or not in PATH"
        return 1
    fi
    return 0
}

check_node_version() {
    local node_version=$(node --version 2>/dev/null | sed 's/v//')
    local required_major=18
    
    if [ -z "$node_version" ]; then
        print_error "Node.js not found"
        return 1
    fi
    
    local major_version=$(echo "$node_version" | cut -d. -f1)
    if [ "$major_version" -lt "$required_major" ]; then
        print_error "Node.js version $node_version found, but version $required_major+ required"
        return 1
    fi
    
    print_success "Node.js version $node_version found"
    return 0
}

check_python_version() {
    local python_version=$(python3 --version 2>/dev/null | cut -d' ' -f2)
    local required_major=3
    local required_minor=8
    
    if [ -z "$python_version" ]; then
        print_error "Python3 not found"
        return 1
    fi
    
    local major_version=$(echo "$python_version" | cut -d. -f1)
    local minor_version=$(echo "$python_version" | cut -d. -f2)
    
    if [ "$major_version" -lt "$required_major" ] || [ "$minor_version" -lt "$required_minor" ]; then
        print_error "Python version $python_version found, but version $required_major.$required_minor+ required"
        return 1
    fi
    
    print_success "Python version $python_version found"
    return 0
}

check_port_available() {
    local port=$1
    local service_name=$2
    
    if lsof -i:$port &>/dev/null; then
        print_error "Port $port is already in use (required for $service_name)"
        print_info "Please stop the service using this port or run: lsof -ti:$port | xargs kill -9"
        return 1
    fi
    return 0
}

# Environment setup functions
setup_directories() {
    print_loading "Setting up directories..."
    
    # Create logs directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Create ML service data directories
    mkdir -p "$PROJECT_ROOT/services/ml-service/data/models"
    mkdir -p "$PROJECT_ROOT/services/ml-service/data/vectordb"
    mkdir -p "$PROJECT_ROOT/services/ml-service/data/docs"
    
    print_success "Directories created successfully"
    return 0
}

setup_python_environment() {
    print_loading "Setting up Python environment for ML service..."
    
    cd "$PROJECT_ROOT/services/ml-service"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            print_error "Failed to create Python virtual environment"
            return 1
        fi
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check if requirements are already installed
    if [ ! -f "venv/.requirements_installed" ]; then
        print_loading "Installing Python dependencies... (this may take a few minutes)"
        
        # Upgrade pip, setuptools, and wheel first to avoid installation issues
        pip install --upgrade pip setuptools wheel
        
        # Try to install requirements with retry logic (up to 3 attempts)
        local max_attempts=3
        local attempt=1
        local install_success=0
        
        while [ $attempt -le $max_attempts ] && [ $install_success -eq 0 ]; do
            print_info "Installation attempt $attempt of $max_attempts..."
            
            # Install requirements with timeout and no-compile flag to avoid syntax errors in legacy packages
            timeout $DEPENDENCY_INSTALL_TIMEOUT pip install --no-compile -r requirements.txt
            
            if [ $? -eq 0 ]; then
                install_success=1
                print_success "Python dependencies installed successfully on attempt $attempt"
            else
                if [ $attempt -lt $max_attempts ]; then
                    print_warning "Installation attempt $attempt failed, retrying..."
                    
                    # Clear pip cache to avoid corrupted downloads
                    print_info "Clearing pip cache..."
                    pip cache purge 2>/dev/null || true
                    
                    # Wait before retry with exponential backoff
                    local wait_time=$((attempt * 5))
                    print_info "Waiting ${wait_time} seconds before retry..."
                    sleep $wait_time
                else
                    print_error "Failed to install Python dependencies after $max_attempts attempts"
                    return 1
                fi
            fi
            
            attempt=$((attempt + 1))
        done
        
        # Mark requirements as installed only if successful
        if [ $install_success -eq 1 ]; then
            touch venv/.requirements_installed
        fi
    else
        print_success "Python dependencies already installed"
    fi
    
    cd "$PROJECT_ROOT"
    return 0
}

setup_node_environment() {
    print_loading "Setting up Node.js environment..."
    
    cd "$PROJECT_ROOT"
    
    # Check if node_modules exists and is recent
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/.install_complete" ]; then
        print_loading "Installing Node.js dependencies... (this may take a few minutes)"
        
        # Determine package manager
        if [ -f "pnpm-lock.yaml" ]; then
            # Check if pnpm is available
            if command -v pnpm &> /dev/null; then
                timeout $DEPENDENCY_INSTALL_TIMEOUT pnpm install
            else
                print_warning "pnpm-lock.yaml found but pnpm not installed, falling back to npm"
                timeout $DEPENDENCY_INSTALL_TIMEOUT npm install
            fi
        else
            timeout $DEPENDENCY_INSTALL_TIMEOUT npm install
        fi
        
        if [ $? -ne 0 ]; then
            print_error "Failed to install Node.js dependencies"
            return 1
        fi
        
        # Mark installation as complete
        touch node_modules/.install_complete
        print_success "Node.js dependencies installed successfully"
    else
        print_success "Node.js dependencies already installed"
    fi
    
    return 0
}

setup_environment_files() {
    print_loading "Setting up environment files..."
    
    # Copy main .env file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ] && [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        print_success "Created .env from .env.example"
    fi
    
    # Copy ML service .env file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/services/ml-service/.env" ] && [ -f "$PROJECT_ROOT/services/ml-service/.env.example" ]; then
        cp "$PROJECT_ROOT/services/ml-service/.env.example" "$PROJECT_ROOT/services/ml-service/.env"
        print_success "Created ML service .env from .env.example"
    fi
    
    # Copy backend .env file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/apps/backend/.env" ] && [ -f "$PROJECT_ROOT/apps/backend/.env.example" ]; then
        cp "$PROJECT_ROOT/apps/backend/.env.example" "$PROJECT_ROOT/apps/backend/.env"
        print_success "Created backend .env from .env.example"
    fi
    
    return 0
}

# Health check functions
wait_for_service_health() {
    local service_name=$1
    local health_url=$2
    local timeout=$3
    
    print_loading "Waiting for $service_name to become healthy..."
    
    local count=0
    while [ $count -lt $timeout ]; do
        if curl -f -s "$health_url" > /dev/null 2>&1; then
            print_success "$service_name is healthy and ready!"
            return 0
        fi
        
        echo -n "."
        sleep 1
        count=$((count + 1))
    done
    
    echo "" # New line after dots
    print_error "$service_name failed to become healthy within $timeout seconds"
    return 1
}

wait_for_service_port() {
    local service_name=$1
    local port=$2
    local timeout=$3
    
    print_loading "Waiting for $service_name to start on port $port..."
    
    local count=0
    while [ $count -lt $timeout ]; do
        if nc -z localhost $port 2>/dev/null; then
            print_success "$service_name is listening on port $port!"
            return 0
        fi
        
        echo -n "."
        sleep 1
        count=$((count + 1))
    done
    
    echo "" # New line after dots
    print_error "$service_name failed to start on port $port within $timeout seconds"
    return 1
}

# Service startup functions
start_ml_service() {
    print_step "Starting ML Service..."
    
    cd "$PROJECT_ROOT/services/ml-service"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Start the service in background
    nohup python -m app.main > "$PROJECT_ROOT/logs/ml-service.log" 2>&1 &
    local ml_pid=$!
    
    # Save PID for later cleanup
    echo $ml_pid > "$PROJECT_ROOT/logs/ml-service.pid"
    
    print_success "ML Service started with PID $ml_pid"
    
    # Wait for the service to be ready
    if ! wait_for_service_port "ML Service" $ML_SERVICE_PORT $SERVICE_START_TIMEOUT; then
        return 1
    fi
    
    # Additional health check if endpoint is available
    sleep 2
    if curl -f -s "http://localhost:$ML_SERVICE_PORT/api/v1/health" > /dev/null 2>&1; then
        print_success "ML Service health check passed"
    else
        print_warning "ML Service is running but health endpoint not responding (this may be normal)"
    fi
    
    cd "$PROJECT_ROOT"
    return 0
}

start_backend_service() {
    print_step "Starting Backend Service..."
    
    cd "$PROJECT_ROOT"
    
    # Start the backend service in background
    nohup npx nx serve backend > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
    local backend_pid=$!
    
    # Save PID for later cleanup
    echo $backend_pid > "$PROJECT_ROOT/logs/backend.pid"
    
    print_success "Backend Service started with PID $backend_pid"
    
    # Wait for the service to be ready
    if ! wait_for_service_port "Backend Service" $BACKEND_PORT $SERVICE_START_TIMEOUT; then
        return 1
    fi
    
    # Additional health check if endpoint is available
    sleep 2
    if curl -f -s "http://localhost:$BACKEND_PORT/api/v1/health" > /dev/null 2>&1; then
        print_success "Backend Service health check passed"
    else
        print_warning "Backend Service is running but health endpoint not responding (this may be normal)"
    fi
    
    return 0
}

start_frontend_service() {
    print_step "Starting Frontend Service..."
    
    cd "$PROJECT_ROOT"
    
    # Start the frontend service in background
    nohup npx nx serve frontend > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
    local frontend_pid=$!
    
    # Save PID for later cleanup
    echo $frontend_pid > "$PROJECT_ROOT/logs/frontend.pid"
    
    print_success "Frontend Service started with PID $frontend_pid"
    
    # Wait for the service to be ready
    if ! wait_for_service_port "Frontend Service" $FRONTEND_PORT $SERVICE_START_TIMEOUT; then
        return 1
    fi
    
    # Check if frontend is serving content
    sleep 3
    if curl -f -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
        print_success "Frontend Service is serving content"
    else
        print_warning "Frontend Service is running but not serving content yet (this may be normal during startup)"
    fi
    
    return 0
}

# Main execution
main() {
    clear
    echo ""
    echo "=========================================="
    echo "🏥 Data Doctor - Local Development Setup"
    echo "=========================================="
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Step 1: Check prerequisites
    print_step "Checking prerequisites..."
    
    if ! check_command "node"; then
        print_error "Please install Node.js (https://nodejs.org/)"
        exit 1
    fi
    
    if ! check_command "python3"; then
        print_error "Please install Python 3.8+ (https://python.org/)"
        exit 1
    fi
    
    if ! check_command "curl"; then
        print_error "Please install curl"
        exit 1
    fi
    
    if ! check_command "lsof"; then
        print_error "Please install lsof"
        exit 1
    fi
    
    if ! check_command "nc"; then
        print_error "Please install netcat (nc)"
        exit 1
    fi
    
    if ! check_node_version; then
        exit 1
    fi
    
    if ! check_python_version; then
        exit 1
    fi
    
    # Check port availability
    if ! check_port_available $ML_SERVICE_PORT "ML Service"; then
        exit 1
    fi
    
    if ! check_port_available $BACKEND_PORT "Backend Service"; then
        exit 1
    fi
    
    if ! check_port_available $FRONTEND_PORT "Frontend Service"; then
        exit 1
    fi
    
    print_success "All prerequisites check passed!"
    echo ""
    
    # Step 2: Environment setup
    print_step "Setting up environment..."
    
    if ! setup_directories; then
        exit 1
    fi
    
    if ! setup_environment_files; then
        exit 1
    fi
    
    if ! setup_python_environment; then
        exit 1
    fi
    
    if ! setup_node_environment; then
        exit 1
    fi
    
    print_success "Environment setup completed!"
    echo ""
    
    # Step 3: Start services in order
    print_step "Starting services in dependency order..."
    echo ""
    
    # Start ML Service first (backend depends on it)
    if ! start_ml_service; then
        print_error "Failed to start ML Service"
        exit 1
    fi
    echo ""
    
    # Start Backend Service (frontend depends on it)
    if ! start_backend_service; then
        print_error "Failed to start Backend Service"
        exit 1
    fi
    echo ""
    
    # Start Frontend Service last
    if ! start_frontend_service; then
        print_error "Failed to start Frontend Service"
        exit 1
    fi
    echo ""
    
    # Final success message
    print_success "🎉 All services started successfully!"
    echo ""
    echo "=========================================="
    echo "📱 Service URLs:"
    echo "----------------------------------------"
    echo "🤖 ML Service:      http://localhost:$ML_SERVICE_PORT"
    echo "🔧 Backend API:     http://localhost:$BACKEND_PORT"
    echo "🌐 Frontend App:    http://localhost:$FRONTEND_PORT"
    echo "----------------------------------------"
    echo "📋 API Documentation:"
    echo "🤖 ML Service:      http://localhost:$ML_SERVICE_PORT/docs"
    echo "🔧 Backend API:     http://localhost:$BACKEND_PORT/api"
    echo "=========================================="
    echo ""
    print_info "💡 To view real-time logs:"
    echo "   ML Service:  tail -f logs/ml-service.log"
    echo "   Backend:     tail -f logs/backend.log"
    echo "   Frontend:    tail -f logs/frontend.log"
    echo ""
    print_info "🛑 To stop all services, press Ctrl+C or run:"
    echo "   kill \$(cat logs/*.pid)"
    echo ""
    print_info "🔄 Services will continue running in the background"
    print_info "👀 Monitor this terminal for any issues or press Ctrl+C to stop all services"
    echo ""
    
    # Keep script running to maintain trap
    while true; do
        sleep 5
        
        # Check if all services are still running
        local services_down=0
        for service in ml-service backend frontend; do
            if [ -f "logs/${service}.pid" ]; then
                local pid=$(cat "logs/${service}.pid")
                if ! kill -0 "$pid" 2>/dev/null; then
                    print_warning "$service has stopped unexpectedly"
                    rm -f "logs/${service}.pid"
                    services_down=$((services_down + 1))
                fi
            fi
        done
        
        if [ $services_down -gt 0 ]; then
            print_error "$services_down service(s) have stopped. Please check the logs and restart."
            break
        fi
    done
}

# Run main function
main "$@"