#!/bin/bash
# Complete Deployment Script for Jetson Orin Nano
# AI Meeting Transcription Assistant

set -e  # Exit on any error

echo "🚀 Starting AI Meeting Transcription Assistant deployment on Jetson Orin Nano..."
echo "=================================================================="

# Configuration
APP_DIR="/opt/ai-meeting-notes"
SERVICE_NAME="jetson-ai-meeting-notes"
NGINX_SITE="ai-meeting-notes"
USER="ubuntu"
GROUP="ubuntu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root. Please run as a regular user with sudo privileges."
   exit 1
fi

# Check if running on Jetson
if ! grep -q "jetson" /proc/device-tree/model 2>/dev/null; then
    log_warning "Not detected as Jetson hardware. Continuing anyway..."
fi

# Step 1: System preparation
log_info "Step 1: Preparing system..."
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev build-essential
sudo apt install -y nginx ffmpeg libsndfile1-dev portaudio19-dev
sudo apt install -y git curl wget htop iotop

# Step 2: Create application directory
log_info "Step 2: Setting up application directory..."
sudo mkdir -p $APP_DIR/{logs,uploads,cache}
sudo chown -R $USER:$GROUP $APP_DIR

# Step 3: Clone or update repository
log_info "Step 3: Setting up application code..."
if [ -d "$APP_DIR/.git" ]; then
    log_info "Updating existing repository..."
    cd $APP_DIR
    git pull origin main
else
    log_info "Cloning repository..."
    cd /opt
    sudo rm -rf ai-meeting-notes
    sudo git clone https://github.com/kaunghtut24/hybrid-transcription.git ai-meeting-notes
    sudo chown -R $USER:$GROUP $APP_DIR
    cd $APP_DIR
fi

# Step 4: Python environment setup
log_info "Step 4: Setting up Python environment..."
if [ -d "venv" ]; then
    log_info "Removing existing virtual environment..."
    rm -rf venv
fi

python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn eventlet psutil

# Step 5: Configuration
log_info "Step 5: Setting up configuration..."

# Copy Jetson-specific configuration files
if [ -f ".env.jetson" ]; then
    cp .env.jetson .env
    log_success "Jetson configuration copied"
else
    log_warning "Jetson configuration not found, using default"
    cp .env.example .env
fi

# Generate secret key if not set
if grep -q "your-secure-random-secret-key" .env; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/your-secure-random-secret-key-generate-this/$SECRET_KEY/" .env
    log_success "Generated new secret key"
fi

# Step 6: Systemd service setup
log_info "Step 6: Setting up systemd service..."
if [ -f "jetson-ai-meeting-notes.service" ]; then
    sudo cp jetson-ai-meeting-notes.service /etc/systemd/system/
else
    log_error "Service file not found!"
    exit 1
fi

# Update service file with correct user
sudo sed -i "s/User=ubuntu/User=$USER/" /etc/systemd/system/$SERVICE_NAME.service
sudo sed -i "s/Group=ubuntu/Group=$GROUP/" /etc/systemd/system/$SERVICE_NAME.service

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# Step 7: Nginx setup
log_info "Step 7: Setting up Nginx..."
if [ -f "nginx-jetson.conf" ]; then
    sudo cp nginx-jetson.conf /etc/nginx/sites-available/$NGINX_SITE
    
    # Update server name with local IP
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    sudo sed -i "s/192.168.1.100/$LOCAL_IP/" /etc/nginx/sites-available/$NGINX_SITE
    
    # Enable site
    sudo ln -sf /etc/nginx/sites-available/$NGINX_SITE /etc/nginx/sites-enabled/
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    if sudo nginx -t; then
        log_success "Nginx configuration is valid"
    else
        log_error "Nginx configuration is invalid"
        exit 1
    fi
else
    log_error "Nginx configuration file not found!"
    exit 1
fi

# Step 8: Firewall setup
log_info "Step 8: Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from 192.168.0.0/16  # Allow local network

# Step 9: Apply Jetson optimizations
log_info "Step 9: Applying Jetson optimizations..."
if [ -f "jetson-optimize.sh" ]; then
    chmod +x jetson-optimize.sh
    ./jetson-optimize.sh
else
    log_warning "Jetson optimization script not found"
fi

# Step 10: Start services
log_info "Step 10: Starting services..."
sudo systemctl start $SERVICE_NAME
sudo systemctl restart nginx

# Wait for service to start
sleep 5

# Step 11: Verify deployment
log_info "Step 11: Verifying deployment..."
if systemctl is-active --quiet $SERVICE_NAME; then
    log_success "Application service is running"
else
    log_error "Application service failed to start"
    sudo journalctl -u $SERVICE_NAME --no-pager -n 20
    exit 1
fi

if systemctl is-active --quiet nginx; then
    log_success "Nginx is running"
else
    log_error "Nginx failed to start"
    exit 1
fi

# Step 12: Run tests
log_info "Step 12: Running validation tests..."
if [ -f "jetson-test-suite.py" ]; then
    python3 jetson-test-suite.py
    if [ $? -eq 0 ]; then
        log_success "All tests passed!"
    else
        log_warning "Some tests failed. Check test-results.json for details."
    fi
else
    log_warning "Test suite not found, skipping tests"
fi

# Step 13: Display deployment information
log_info "Step 13: Deployment complete!"
echo "=================================================================="
echo -e "${GREEN}🎉 AI Meeting Transcription Assistant deployed successfully!${NC}"
echo ""
echo "📋 Deployment Information:"
echo "  • Application Directory: $APP_DIR"
echo "  • Service Name: $SERVICE_NAME"
echo "  • Local Access: http://$(hostname -I | awk '{print $1}')"
echo "  • Logs: $APP_DIR/logs/"
echo ""
echo "🔧 Management Commands:"
echo "  • Start service: sudo systemctl start $SERVICE_NAME"
echo "  • Stop service: sudo systemctl stop $SERVICE_NAME"
echo "  • Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  • View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "  • Monitor system: $APP_DIR/monitor.sh"
echo ""
echo "⚙️ Configuration:"
echo "  • Edit environment: nano $APP_DIR/.env"
echo "  • Nginx config: /etc/nginx/sites-available/$NGINX_SITE"
echo "  • Service config: /etc/systemd/system/$SERVICE_NAME.service"
echo ""
echo "🌐 Next Steps:"
echo "  1. Configure your API keys in $APP_DIR/.env"
echo "  2. Set up dynamic DNS for external access (optional)"
echo "  3. Configure SSL certificate (optional)"
echo "  4. Test the application in your browser"
echo ""
echo "📞 Support:"
echo "  • Check logs if issues occur"
echo "  • Run monitor script for system status"
echo "  • Ensure API keys are properly configured"
echo "=================================================================="

log_success "Deployment completed successfully! 🚀"
