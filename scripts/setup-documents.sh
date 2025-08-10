#!/bin/bash

# setup-documents.sh - Process documents for the ML service
# This script must be run before start-local.sh on fresh installations

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

# Navigate to ML service directory
cd services/ml-service

# Check if Python virtual environment exists
if [[ ! -d "venv" ]]; then
    print_error "Python virtual environment not found"
    print_error "Please run ./scripts/start-local.sh first to set up the environment"
    exit 1
fi

print_info "Activating Python virtual environment..."
source venv/bin/activate

# Check if required packages are installed
if ! python -c "import fastapi, requests" 2>/dev/null; then
    print_error "Required Python packages not installed"
    print_error "Please run ./scripts/start-local.sh first to install dependencies"
    exit 1
fi

print_success "Environment ready"

# Start ML service temporarily for document processing
print_info "Starting ML service temporarily for document processing..."
print_loading "This will start the server, process documents, then stop..."

# Start the ML service in background
python -m app.main &
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
max_attempts=30
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
    print_error "ML service failed to start within 30 seconds"
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