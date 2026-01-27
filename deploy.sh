#!/bin/bash
# Deploy script for PayPort Bot
# Usage: ./deploy.sh user@server-ip

set -e

if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh user@server-ip"
    echo "Example: ./deploy.sh root@123.45.67.89"
    exit 1
fi

SERVER=$1
REMOTE_DIR="/opt/payport_bot"

echo "🚀 Deploying to $SERVER..."

# Create remote directory
ssh $SERVER "mkdir -p $REMOTE_DIR"

# Sync files (excluding unnecessary)
rsync -avz --progress \
    --exclude 'venv/' \
    --exclude '*.db' \
    --exclude 'generated_docs/' \
    --exclude '.git/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.env' \
    ./ $SERVER:$REMOTE_DIR/

echo "📦 Installing dependencies on server..."

ssh $SERVER << 'ENDSSH'
cd /opt/payport_bot

# Install Python if needed
if ! command -v python3.11 &> /dev/null; then
    apt update && apt install python3.11 python3.11-venv -y
fi

# Create venv and install deps
python3.11 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# Create systemd service
cat > /etc/systemd/system/payport-bot.service << 'EOF'
[Unit]
Description=PayPort Questionnaire Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/payport_bot
Environment=PATH=/opt/payport_bot/venv/bin
ExecStart=/opt/payport_bot/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable payport-bot

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  ВАЖНО: Создайте файл .env на сервере:"
    echo "    nano /opt/payport_bot/.env"
    echo ""
    echo "    Содержимое:"
    echo "    BOT_TOKEN=your_token_here"
    echo "    FIRST_ADMIN_USERNAME=AlbuRx"
else
    systemctl restart payport-bot
    echo "✅ Bot restarted!"
fi
ENDSSH

echo ""
echo "✅ Deploy complete!"
echo ""
echo "Next steps on server:"
echo "1. Create .env: nano /opt/payport_bot/.env"
echo "2. Start bot: systemctl start payport-bot"
echo "3. Check logs: journalctl -u payport-bot -f"

