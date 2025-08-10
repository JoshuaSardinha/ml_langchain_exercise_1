#!/bin/bash

# setup-documents.sh - Process documents for the ML service
# This script works independently on fresh installations

set -euo pipefail

# Colors and formatting for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_loading() { echo -e "${YELLOW}[LOADING]${NC} $1"; }
print_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Configuration
DEPENDENCY_INSTALL_TIMEOUT=300

# Prerequisites checking functions
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed or not in PATH"
        return 1
    fi
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

# Environment setup functions
setup_directories() {
    print_loading "Setting up directories..."
    
    # Create ML service data directories
    mkdir -p "services/ml-service/data/models"
    mkdir -p "services/ml-service/data/vectordb"
    mkdir -p "services/ml-service/data/docs"
    
    print_success "Directories created successfully"
    return 0
}

setup_environment_files() {
    print_loading "Setting up environment files..."
    
    # Copy ML service .env file if it doesn't exist
    if [ ! -f "services/ml-service/.env" ] && [ -f "services/ml-service/.env.example" ]; then
        cp "services/ml-service/.env.example" "services/ml-service/.env"
        print_success "Created ML service .env from .env.example"
    fi
    
    return 0
}

setup_python_environment() {
    print_loading "Setting up Python environment for ML service..."
    
    cd "services/ml-service"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            print_error "Failed to create Python virtual environment"
            cd "../.."
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
                    cd "../.."
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
    
    cd "../.."
    return 0
}

# Script header
echo ""
echo "=================================================="
echo "📄 DATA DOCTOR - DOCUMENT PROCESSING SETUP"
echo "=================================================="
echo ""

# Check if we're in the right directory
if [[ ! -f "services/ml-service/requirements.txt" ]]; then
    print_error "This script must be run from the project root directory"
    print_error "Expected to find: services/ml-service/requirements.txt"
    exit 1
fi

print_info "Setting up document processing for ML service..."

# Step 1: Check prerequisites
print_step "Checking prerequisites..."

if ! check_command "python3"; then
    print_error "Please install Python 3.8+ (https://python.org/)"
    exit 1
fi

if ! check_command "curl"; then
    print_error "Please install curl"
    exit 1
fi

if ! check_python_version; then
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

print_success "Environment setup completed!"
echo ""

# Navigate to ML service directory
cd services/ml-service

print_info "Activating Python virtual environment..."
source venv/bin/activate

print_success "Environment ready"

# Start ML service temporarily for document processing
print_info "Starting ML service temporarily for document processing..."
print_loading "This will start the server, process documents, then stop..."

# Start the ML service in background (redirect output to reduce noise)
python -m app.main > /dev/null 2>&1 &
ML_SERVICE_PID=$!

# Function to cleanup on exit
cleanup() {
    if ps -p $ML_SERVICE_PID > /dev/null 2>&1; then
        print_info "Stopping ML service (PID: $ML_SERVICE_PID)..."
        kill $ML_SERVICE_PID
        wait $ML_SERVICE_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Wait for service to start
print_loading "Waiting for ML service to start..."
max_attempts=120
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f -s "http://localhost:8000/api/v1/health" > /dev/null 2>&1; then
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
    echo -n "."
done
echo ""

if [ $attempt -eq $max_attempts ]; then
    print_error "ML service failed to start within 120 seconds"
    exit 1
fi

print_success "ML service started successfully"

# Process documents
print_info "Processing documents via API endpoint..."
print_loading "This may take a few minutes depending on document size..."

# Call the document processing endpoint
response=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8000/api/v1/docs/process?force_reprocess=true")
http_code=$(echo "$response" | tail -n1)
response_body=$(echo "$response" | sed '$d')

if [ "$http_code" -eq 200 ]; then
    print_success "Document processing completed successfully!"
    
    # Parse and display results if possible
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json
import sys
try:
    data = json.loads('$response_body')
    if 'documents_processed' in data:
        print('📄 Documents processed: {}'.format(data['documents_processed']))
    if 'total_chunks' in data:
        print('🧩 Total chunks created: {}'.format(data['total_chunks']))
    if 'status' in data:
        print('📊 Status: {}'.format(data['status']))
except:
    pass
" 2>/dev/null || true
    fi
else
    print_error "Document processing failed (HTTP $http_code)"
    print_error "Response: $response_body"
    exit 1
fi

# Verify document processing worked
print_info "Verifying document processing..."
stats_response=$(curl -s -w "\n%{http_code}" "http://localhost:8000/api/v1/docs/stats")
stats_http_code=$(echo "$stats_response" | tail -n1)
stats_body=$(echo "$stats_response" | sed '$d')

if [ "$stats_http_code" -eq 200 ]; then
    print_success "Document processing verification successful!"
    
    # Display stats
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json
try:
    data = json.loads('$stats_body')
    if 'total_chunks' in data:
        print('✅ Vector database contains {} document chunks'.format(data['total_chunks']))
    if 'llm_configured' in data:
        print('🤖 LLM configured: {}'.format(data['llm_configured']))
    if 'rag_chain_available' in data:
        print('🔗 RAG chain available: {}'.format(data['rag_chain_available']))
except:
    pass
" 2>/dev/null || true
    fi
else
    print_warning "Could not verify document stats (HTTP $stats_http_code)"
fi

print_success "Document setup completed successfully!"
echo ""
echo "=================================================="
echo "🎉 DOCUMENT PROCESSING SETUP COMPLETE"
echo "=================================================="
echo ""
print_info "You can now run: ./scripts/start-local.sh"
print_info "The ML service will have access to processed documents"
echo ""