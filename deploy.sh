#!/bin/bash
set -e

# ============================================================
# RBX TOOL - UBUNTU 24.04 DEPLOY SCRIPT
# ============================================================

echo "🚀 RBX Tool Deploy Script"
echo "📍 VPS: Ubuntu 24.04.4 LTS"
echo "⏱️  $(date)"
echo ""

# ============================================================
# 1. SYSTEM UPDATE
# ============================================================
echo "📦 [1/10] Updating system packages..."
apt update
apt upgrade -y

# ============================================================
# 2. INSTALL DEPENDENCIES
# ============================================================
echo "📦 [2/10] Installing Python, pip, git, curl, nginx..."
apt install -y python3 python3-pip python3-venv git curl nginx

# ============================================================
# 3. CREATE PROJECT DIRECTORY
# ============================================================
echo "📁 [3/10] Creating project directory..."
PROJECT_DIR="/home/rbxtool"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# ============================================================
# 4. CLONE/COPY PROJECT (Option: Manual setup)
# ============================================================
echo "📥 [4/10] Setting up project files..."
if [ -d ".git" ]; then
    echo "   ✅ Git repo already exists, pulling latest..."
    git pull origin main 2>/dev/null || echo "   ⚠️  Pull failed, skipping"
else
    echo "   ⚠️  Assuming files already copied to $PROJECT_DIR"
    echo "   💡 Copy your project files here: $PROJECT_DIR"
fi

# ============================================================
# 5. CREATE PYTHON VIRTUAL ENV
# ============================================================
echo "🐍 [5/10] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# ============================================================
# 6. INSTALL PYTHON DEPENDENCIES
# ============================================================
echo "📦 [6/10] Installing Python packages..."
pip install --upgrade pip
pip install flask flask-cors discord.py apscheduler python-dotenv requests gunicorn

# ============================================================
# 7. CREATE .ENV FILE
# ============================================================
echo "⚙️  [7/10] Creating .env file..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_token_here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_URL_UPDATES=https://discord.com/api/webhooks/...

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Cookie Configuration
REFRESH_INTERVAL_MINUTES=30
COOKIE_MAX_AGE_HOURS=5

# Flask Configuration
SECRET_KEY=rbx-secret-key-2024-session
PORT=5000
EOF
    echo "   ✅ Created .env template"
    echo "   ⚠️  EDIT THIS FILE: nano .env"
    echo "   Add your Discord webhooks and tokens!"
else
    echo "   ✅ .env already exists"
fi

# ============================================================
# 8. CREATE SYSTEMD SERVICE
# ============================================================
echo "🔧 [8/10] Creating systemd service..."
cat > /etc/systemd/system/rbxtool.service << EOF
[Unit]
Description=RBX Tool - Roblox Account Manager
After=network.target
Wants=network-online.target

[Service]
Type=notify
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5000 --timeout 120 app:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable rbxtool.service
echo "   ✅ Created systemd service: rbxtool.service"

# ============================================================
# 9. CONFIGURE NGINX
# ============================================================
echo "🌐 [9/10] Configuring Nginx..."
cat > /etc/nginx/sites-available/rbxtool << 'EOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
    }

    location /static/ {
        alias /home/rbxtool/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Remove default config if exists
rm -f /etc/nginx/sites-enabled/default

# Enable rbxtool config
ln -sf /etc/nginx/sites-available/rbxtool /etc/nginx/sites-enabled/rbxtool

# Test Nginx config
nginx -t

systemctl enable nginx
systemctl restart nginx
echo "   ✅ Nginx configured and restarted"

# ============================================================
# 10. DATABASE INIT (app.py will handle it)
# ============================================================
echo "💾 [10/10] Database setup..."
echo "   ℹ️  app.py will auto-initialize SQLite database on first run"
echo "   📁 Database location: $PROJECT_DIR/rbx_sessions.db"

# ============================================================
# FINAL SETUP
# ============================================================
echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1️⃣  Edit .env file:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2️⃣  Add your Discord webhooks:"
echo "   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK"
echo "   DISCORD_WEBHOOK_URL_UPDATES=https://discord.com/api/webhooks/YOUR_WEBHOOK"
echo ""
echo "3️⃣  Start the application:"
echo "   systemctl start rbxtool"
echo ""
echo "4️⃣  Check status:"
echo "   systemctl status rbxtool"
echo ""
echo "5️⃣  View logs:"
echo "   journalctl -u rbxtool -f"
echo ""
echo "6️⃣  Access web interface:"
echo "   http://103.38.236.58"
echo "   http://103.38.236.58/admin (login: admin / admin123)"
echo ""
echo "7️⃣  Optional: Setup SSL with Let's Encrypt"
echo "   sudo apt install certbot python3-certbot-nginx -y"
echo "   sudo certbot --nginx -d your-domain.com"
echo ""
echo "🔗 Project Directory: $PROJECT_DIR"
echo "📝 Logs: journalctl -u rbxtool -f"
echo "🔧 Config: $PROJECT_DIR/.env"
echo ""
