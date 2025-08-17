# AI Meeting Transcription Assistant - Cloud Deployment Guide

This guide covers deploying the AI Meeting Transcription Assistant to various cloud platforms with proper CORS configuration and environment variable management.

## 🏗️ Architecture Overview

The application consists of:
- **Frontend**: Static HTML/CSS/JavaScript with real-time WebSocket support
- **Backend**: Flask API server with SocketIO for real-time communication
- **Services**: Integration with AssemblyAI and Google Gemini AI APIs
- **Health Checks**: Built-in endpoints for cloud platform monitoring

## 📋 Prerequisites

1. **API Keys**: Obtain API keys from:
   - [AssemblyAI](https://www.assemblyai.com/dashboard/) for real-time transcription
   - [Google AI Studio](https://ai.google.dev/) for Gemini AI features

2. **Environment Variables**: Configure based on `.env.example`
3. **Git Repository**: Code should be in a Git repository for cloud deployments

## 🔧 Environment Configuration

### Core Environment Variables

```bash
# Required
SECRET_KEY=your-secure-random-secret-key
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
GEMINI_API_KEY=your-gemini-api-key

# CORS Configuration (comma-separated origins)
CORS_ORIGINS=https://yourdomain.com,https://ai-meetingnotes.vercel.app

# Optional
FLASK_ENV=production
PORT=5000
JWT_EXPIRATION_HOURS=24
```

## 🚀 Deployment Options

### 1. Local Development (Flask)

**Prerequisites:**
- Python 3.9+
- pip

**Setup:**
```bash
# Clone the repository
git clone <your-repo-url>
cd meeting-transcription-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run the application
python app.py
```

**Access:** http://localhost:5000

### 2. Docker Deployment

**Prerequisites:**
- Docker
- Docker Compose

**Setup:**
```bash
# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

**Access:** http://localhost

### 3. Traditional Server (Nginx + Gunicorn)

**Prerequisites:**
- Ubuntu/CentOS server
- Python 3.9+
- Nginx

**Setup:**
```bash
# Install system dependencies
sudo apt update
sudo apt install python3-pip python3-venv nginx

# Create application directory
sudo mkdir -p /var/www/meeting-transcription-ai
sudo chown $USER:$USER /var/www/meeting-transcription-ai

# Clone and setup application
cd /var/www/meeting-transcription-ai
git clone <your-repo-url> .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration

# Install systemd service
sudo cp meeting-transcription-ai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable meeting-transcription-ai
sudo systemctl start meeting-transcription-ai

# Configure Nginx
sudo cp nginx.conf /etc/nginx/sites-available/meeting-transcription-ai
sudo ln -s /etc/nginx/sites-available/meeting-transcription-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. Firebase Hosting + Cloud Functions

**Prerequisites:**
- Firebase CLI
- Google Cloud Project with billing enabled

**Setup:**
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Initialize Firebase project
firebase init

# Select:
# - Hosting
# - Functions (Python)

# Deploy
firebase deploy
```

**Configuration:**
- Set environment variables in Firebase Console
- Configure custom domain if needed

### 5. Vercel Deployment

**Prerequisites:**
- Vercel CLI or GitHub integration
- Vercel account

**Setup via CLI:**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Set environment variables
vercel env add SECRET_KEY
vercel env add JWT_EXPIRATION_HOURS
```

**Setup via GitHub:**
1. Push code to GitHub repository
2. Connect repository to Vercel
3. Configure environment variables in Vercel dashboard
4. Deploy automatically on push

### 6. Google Cloud Platform

**App Engine:**
```bash
# Create app.yaml
echo "runtime: python39" > app.yaml

# Deploy
gcloud app deploy
```

**Cloud Run:**
```bash
# Build and deploy
gcloud run deploy meeting-transcription-ai \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 🔐 Security Configuration

### Environment Variables

**Required:**
- `SECRET_KEY`: Random string for JWT signing
- `JWT_EXPIRATION_HOURS`: Token expiration time (default: 24)

**Optional:**
- `CORS_ORIGINS`: Allowed origins for CORS
- `RATE_LIMIT_PER_MINUTE`: API rate limiting

### SSL/TLS Configuration

**For Nginx:**
```bash
# Obtain SSL certificate (Let's Encrypt)
sudo certbot --nginx -d yourdomain.com
```

**For Cloud Platforms:**
- Most cloud platforms provide automatic SSL
- Configure custom domains in platform settings

## 📊 Monitoring and Logging

### Health Checks
- Endpoint: `/health`
- Returns service status and version

### Logging
- Application logs: `/var/log/meeting-transcription-ai/`
- Nginx logs: `/var/log/nginx/`

### Monitoring
- Set up monitoring for `/health` endpoint
- Monitor API response times and error rates
- Track resource usage (CPU, memory, disk)

## 🔧 Configuration Management

### API Keys
- Users configure their own API keys through the web interface
- Keys are stored securely on the backend
- No API keys are exposed to the frontend

### Service Configuration
- AssemblyAI: Real-time transcription service
- Google Gemini: AI text processing (summarization, translation, keywords)
- Fallback: Web Speech API for transcription, simulated AI for processing

## 🚨 Troubleshooting

### Common Issues

**1. CORS Errors:**
- Check `CORS_ORIGINS` environment variable
- Ensure proper domain configuration

**2. API Key Issues:**
- Verify API keys are valid and have proper permissions
- Check API quotas and billing

**3. WebSocket Connection Failures:**
- Ensure WebSocket support in proxy configuration
- Check firewall settings for WebSocket traffic

**4. Performance Issues:**
- Increase worker processes for high traffic
- Implement Redis for session storage
- Use CDN for static assets

### Logs and Debugging

**Flask Application:**
```bash
# View application logs
tail -f /var/log/meeting-transcription-ai/app.log

# Debug mode (development only)
export FLASK_ENV=development
python app.py
```

**Docker:**
```bash
# View container logs
docker-compose logs -f app

# Access container shell
docker-compose exec app bash
```

## 📈 Scaling Considerations

### Horizontal Scaling
- Use load balancer (Nginx, HAProxy, cloud load balancer)
- Implement Redis for shared session storage
- Use database for persistent API key storage

### Vertical Scaling
- Increase server resources (CPU, RAM)
- Optimize worker processes and threads
- Implement caching strategies

### Database Migration
For production deployments, replace in-memory storage with:
- PostgreSQL for API keys and user data
- Redis for session management and caching

## 🔄 Updates and Maintenance

### Deployment Updates
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Restart services
sudo systemctl restart meeting-transcription-ai
sudo systemctl reload nginx
```

### Backup Strategy
- Regular database backups
- Configuration file backups
- SSL certificate backups

## 📞 Support

For deployment issues:
1. Check logs for error messages
2. Verify environment configuration
3. Test API endpoints manually
4. Check service status and connectivity
