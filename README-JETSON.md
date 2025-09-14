# AI Meeting Transcription - Jetson Orin Nano Deployment Guide

## 🚀 **Complete Home Server Setup for Jetson Orin Nano with JetPack 6.2**

This guide provides step-by-step instructions for deploying the AI Meeting Transcription system on your Jetson Orin Nano as a home server.

---

## 📋 **Prerequisites**

### Hardware Requirements
- **Jetson Orin Nano Developer Kit** with JetPack 6.2
- **64GB+ microSD card** (Class 10 or better)
- **Stable internet connection** (for API services)
- **Ethernet connection** (recommended for stability)

### Software Requirements
- **JetPack 6.2** installed and configured
- **SSH access** to your Jetson
- **API Keys** from:
  - [AssemblyAI](https://www.assemblyai.com/dashboard/) (for transcription)
  - [Google AI Studio](https://ai.google.dev/) (for AI analysis)

---

## 🛠️ **Quick Deployment**

### **Option 1: Automated Deployment (Recommended)**

```bash
# 1. SSH into your Jetson Orin Nano
ssh ubuntu@your-jetson-ip

# 2. Clone the repository
git clone https://github.com/kaunghtut24/hybrid-transcription.git
cd hybrid-transcription

# 3. Make deployment script executable
chmod +x deploy-jetson.sh

# 4. Run the automated deployment
./deploy-jetson.sh

# 5. Configure your API keys
nano /opt/ai-meeting-notes/.env
# Add your ASSEMBLYAI_API_KEY and GEMINI_API_KEY

# 6. Restart the service
sudo systemctl restart jetson-ai-meeting-notes
```

### **Option 2: Manual Step-by-Step**

<details>
<summary>Click to expand manual installation steps</summary>

```bash
# 1. System preparation
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev build-essential
sudo apt install -y nginx ffmpeg libsndfile1-dev portaudio19-dev git

# 2. Create application directory
sudo mkdir -p /opt/ai-meeting-notes/{logs,uploads,cache}
sudo chown -R $USER:$USER /opt/ai-meeting-notes

# 3. Clone repository
cd /opt
sudo git clone https://github.com/kaunghtut24/hybrid-transcription.git ai-meeting-notes
sudo chown -R $USER:$USER /opt/ai-meeting-notes
cd /opt/ai-meeting-notes

# 4. Python environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn eventlet

# 5. Configuration
cp .env.jetson .env
# Edit .env with your API keys

# 6. Install systemd service
sudo cp jetson-ai-meeting-notes.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jetson-ai-meeting-notes

# 7. Configure Nginx
sudo cp nginx-jetson.conf /etc/nginx/sites-available/ai-meeting-notes
sudo ln -s /etc/nginx/sites-available/ai-meeting-notes /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 8. Start services
sudo systemctl start jetson-ai-meeting-notes
sudo systemctl restart nginx
```

</details>

---

## ⚙️ **Configuration**

### **Environment Variables (.env)**

```bash
# Required API Keys
ASSEMBLYAI_API_KEY=your-assemblyai-key-here
GEMINI_API_KEY=your-gemini-key-here

# Server Configuration
SECRET_KEY=your-generated-secret-key
FLASK_ENV=production
PORT=5000
HOST=0.0.0.0

# Performance Settings (Jetson Optimized)
WORKERS=2
WORKER_CLASS=eventlet
TIMEOUT=60
```

### **Network Access**

**Local Network Access:**
- Application will be available at: `http://your-jetson-ip`
- Default port: 80 (HTTP)

**External Access (Optional):**
1. Configure port forwarding on your router (port 80 → Jetson IP)
2. Set up dynamic DNS service (No-IP, DuckDNS, etc.)
3. Configure SSL certificate for HTTPS

---

## 🔧 **Management Commands**

### **Service Management**
```bash
# Start/Stop/Restart service
sudo systemctl start jetson-ai-meeting-notes
sudo systemctl stop jetson-ai-meeting-notes
sudo systemctl restart jetson-ai-meeting-notes

# Check service status
sudo systemctl status jetson-ai-meeting-notes

# View logs
sudo journalctl -u jetson-ai-meeting-notes -f
```

### **System Monitoring**
```bash
# Run monitoring script
/opt/ai-meeting-notes/monitor.sh

# Check system resources
htop
nvidia-smi  # GPU usage

# View application logs
tail -f /opt/ai-meeting-notes/logs/error.log
```

### **Performance Optimization**
```bash
# Apply Jetson optimizations
/opt/ai-meeting-notes/jetson-optimize.sh

# Set maximum performance mode
sudo nvpmodel -m 0
sudo jetson_clocks
```

---

## 🧪 **Testing and Validation**

### **Run Test Suite**
```bash
cd /opt/ai-meeting-notes
python3 jetson-test-suite.py

# Check test results
cat test-results.json
```

### **Manual Testing**
1. **Health Check:** `curl http://your-jetson-ip/health`
2. **Web Interface:** Open browser to `http://your-jetson-ip`
3. **API Test:** Test microphone access and transcription
4. **Performance:** Monitor CPU/memory usage during operation

---

## 📊 **Performance Expectations**

### **Jetson Orin Nano Specifications**
- **CPU:** 6-core ARM Cortex-A78AE @ 1.5GHz
- **GPU:** 1024-core NVIDIA Ampere
- **RAM:** 8GB LPDDR5
- **Expected Performance:**
  - Real-time transcription: ✅ Excellent
  - Concurrent users: 2-5 users
  - Memory usage: ~500MB-1GB
  - CPU usage: ~20-40% under load

### **Resource Usage**
- **Base Application:** ~200-500MB RAM
- **With AI Processing:** ~500MB-1GB RAM
- **Storage:** ~2-5GB total
- **Network:** Dependent on API usage

---

## 🔒 **Security Considerations**

### **Firewall Configuration**
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow from 192.168.0.0/16  # Local network only
```

### **SSL/HTTPS Setup (Optional)**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate (requires domain name)
sudo certbot --nginx -d your-domain.com
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

**Service Won't Start:**
```bash
# Check logs
sudo journalctl -u jetson-ai-meeting-notes --no-pager -n 50

# Check configuration
sudo nginx -t
```

**High Memory Usage:**
```bash
# Restart service to clear memory
sudo systemctl restart jetson-ai-meeting-notes

# Check for memory leaks
/opt/ai-meeting-notes/monitor.sh
```

**API Connection Issues:**
```bash
# Test API keys
curl -H "Authorization: YOUR_ASSEMBLYAI_KEY" https://api.assemblyai.com/v2/transcript

# Check internet connectivity
ping api.assemblyai.com
```

### **Performance Issues**
```bash
# Enable maximum performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Check system resources
htop
iotop
```

---

## 📈 **Monitoring and Maintenance**

### **Log Rotation**
Logs are automatically rotated daily. Check `/etc/logrotate.d/ai-meeting-notes`

### **Backup Strategy**
```bash
# Backup configuration
cp /opt/ai-meeting-notes/.env ~/ai-meeting-notes-backup.env

# Backup logs (optional)
tar -czf ~/logs-backup-$(date +%Y%m%d).tar.gz /opt/ai-meeting-notes/logs/
```

### **Updates**
```bash
cd /opt/ai-meeting-notes
git pull origin main
sudo systemctl restart jetson-ai-meeting-notes
```

---

## 🎯 **Next Steps**

1. **Configure API Keys** - Essential for full functionality
2. **Test All Features** - Verify transcription and AI analysis
3. **Set Up External Access** - Configure router/DNS if needed
4. **Monitor Performance** - Use monitoring tools regularly
5. **Plan Backups** - Regular configuration backups

---

## 📞 **Support**

- **Logs Location:** `/opt/ai-meeting-notes/logs/`
- **Configuration:** `/opt/ai-meeting-notes/.env`
- **Service Status:** `sudo systemctl status jetson-ai-meeting-notes`
- **System Monitor:** `/opt/ai-meeting-notes/monitor.sh`

**For issues:**
1. Check service logs
2. Verify API key configuration
3. Test network connectivity
4. Monitor system resources

---

**🎉 Enjoy your AI-powered meeting transcription home server on Jetson Orin Nano!**
