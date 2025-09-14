#!/bin/bash
# Jetson Orin Nano Optimization Script
# AI Meeting Transcription Assistant

echo "🚀 Optimizing Jetson Orin Nano for AI Meeting Transcription..."

# 1. Enable maximum performance mode
echo "⚡ Setting maximum performance mode..."
sudo nvpmodel -m 0  # Maximum performance mode
sudo jetson_clocks  # Lock clocks to maximum

# 2. Optimize memory settings
echo "🧠 Optimizing memory settings..."
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_ratio=15' | sudo tee -a /etc/sysctl.conf
echo 'vm.dirty_background_ratio=5' | sudo tee -a /etc/sysctl.conf

# 3. Create swap file if needed (for memory-intensive operations)
if [ ! -f /swapfile ]; then
    echo "💾 Creating swap file..."
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# 4. Optimize CPU governor
echo "🔧 Setting CPU governor to performance..."
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 5. Create application directories
echo "📁 Creating application directories..."
sudo mkdir -p /opt/ai-meeting-notes/{logs,uploads,cache}
sudo chown -R $USER:$USER /opt/ai-meeting-notes

# 6. Install monitoring tools
echo "📊 Installing monitoring tools..."
sudo apt install -y htop iotop nethogs

# 7. Configure log rotation
echo "📝 Configuring log rotation..."
sudo tee /etc/logrotate.d/ai-meeting-notes << EOF
/opt/ai-meeting-notes/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload jetson-ai-meeting-notes
    endscript
}
EOF

# 8. Optimize audio settings
echo "🎵 Optimizing audio settings..."
# Increase audio buffer sizes for better real-time performance
echo 'options snd-hda-intel model=generic' | sudo tee -a /etc/modprobe.d/alsa-base.conf

# 9. Network optimizations for real-time audio
echo "🌐 Applying network optimizations..."
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
sudo sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sudo sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"

# 10. Create monitoring script
echo "📈 Creating monitoring script..."
tee /opt/ai-meeting-notes/monitor.sh << 'EOF'
#!/bin/bash
# Simple monitoring script for Jetson deployment

echo "=== Jetson AI Meeting Notes Status ==="
echo "Date: $(date)"
echo ""

echo "=== System Resources ==="
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print $2 $3 $4 $5}'
echo ""

echo "Memory Usage:"
free -h
echo ""

echo "Disk Usage:"
df -h /opt/ai-meeting-notes
echo ""

echo "=== Service Status ==="
systemctl is-active jetson-ai-meeting-notes
systemctl is-active nginx
echo ""

echo "=== Network Status ==="
ss -tlnp | grep :5000
ss -tlnp | grep :80
echo ""

echo "=== Recent Logs ==="
tail -n 5 /opt/ai-meeting-notes/logs/error.log 2>/dev/null || echo "No error logs found"
echo ""

echo "=== GPU Status ==="
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null || echo "GPU monitoring not available"
EOF

chmod +x /opt/ai-meeting-notes/monitor.sh

echo "✅ Jetson optimization complete!"
echo ""
echo "📋 Next steps:"
echo "1. Reboot the system: sudo reboot"
echo "2. Run the monitoring script: /opt/ai-meeting-notes/monitor.sh"
echo "3. Deploy the application using the deployment script"
