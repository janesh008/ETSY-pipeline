# Backend Service

Location:

```bash
/etc/systemd/system/backend.service
```

```ini
[Unit]
Description=CraftDesk Backend
After=network.target

[Service]
Type=simple

User=pixelbloomco1
Group=pixelbloomco1

WorkingDirectory=/home/pixelbloomco1/ETSY-pipeline

Environment=PYTHONUNBUFFERED=1

ExecStart=/home/pixelbloomco1/ETSY-pipeline/venv/bin/python \
    -m uvicorn craftdesk_api.main:app \
    --host 127.0.0.1 \
    --port 8000

Restart=always
RestartSec=5

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Explanation

| Parameter | Description |
|-----------|-------------|
| WorkingDirectory | Root directory of the backend project |
| ExecStart | Starts FastAPI using the project virtual environment |
| Restart=always | Automatically restart if the backend crashes |
| RestartSec=5 | Wait 5 seconds before restarting |
| StandardOutput | Send logs to journalctl |
| StandardError | Send errors to journalctl |

---

# Frontend Service

Location

```bash
/etc/systemd/system/frontend.service
```

```ini
[Unit]
Description=CraftDesk Frontend
After=network.target

[Service]
Type=simple

User=pixelbloomco1
Group=pixelbloomco1

WorkingDirectory=/home/pixelbloomco1/ETSY-pipeline/craftdesk_web

Environment=NODE_ENV=production
Environment="PATH=/home/pixelbloomco1/node-v20.11.0-linux-x64/bin:/usr/local/bin:/usr/bin:/bin"

ExecStart=/home/pixelbloomco1/node-v20.11.0-linux-x64/bin/npm run start

Restart=always
RestartSec=5

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Explanation

| Parameter | Description |
|-----------|-------------|
| WorkingDirectory | Next.js application directory |
| NODE_ENV | Runs Next.js in production mode |
| PATH | Uses Node 20 instead of Ubuntu's older Node installation |
| ExecStart | Starts the production Next.js server |
| Restart=always | Automatically restart after crashes |

> **Important:** Do **not** use `npm run dev` in production.

Before the first deployment execute:

```bash
cd ~/ETSY-pipeline/craftdesk_web

npm install

npm run build
```

---

# ComfyUI Service

Location

```bash
/etc/systemd/system/comfyui.service
```

```ini
[Unit]
Description=ComfyUI
After=network.target

[Service]
Type=simple

User=pixelbloomco1
Group=pixelbloomco1

WorkingDirectory=/opt/ComfyUI

ExecStart=/opt/ComfyUI/venv/bin/python \
    /opt/ComfyUI/main.py \
    --listen 127.0.0.1 \
    --port 8188

Restart=always
RestartSec=5

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Explanation

| Parameter | Description |
|-----------|-------------|
| WorkingDirectory | ComfyUI installation directory |
| ExecStart | Starts ComfyUI |
| Restart=always | Restart automatically after crashes |
| StandardOutput | Logs available through journalctl |

---

# Enable Services

Reload systemd after creating or editing service files.

```bash
sudo systemctl daemon-reload
```

Enable services so they automatically start after every VM boot.

```bash
sudo systemctl enable comfyui
sudo systemctl enable backend
sudo systemctl enable frontend
```

Start services immediately.

```bash
sudo systemctl start comfyui
sudo systemctl start backend
sudo systemctl start frontend
```

---

# Verify Services

```bash
sudo systemctl status comfyui

sudo systemctl status backend

sudo systemctl status frontend
```

Expected output

```
Active: active (running)
```

---

# Restart Services

Restart a single service

```bash
sudo systemctl restart backend
```

```bash
sudo systemctl restart frontend
```

```bash
sudo systemctl restart comfyui
```

Restart all services

```bash
sudo systemctl restart backend frontend comfyui
```

---

# Logs

Backend

```bash
journalctl -u backend -f
```

Frontend

```bash
journalctl -u frontend -f
```

ComfyUI

```bash
journalctl -u comfyui -f
```

Last 100 lines

```bash
journalctl -u frontend -n 100
```

---

# Boot Flow

```
VM Starts
      │
      ▼
Ubuntu Boots
      │
      ▼
systemd
      │
      ├──────────────┐
      │              │
      ▼              ▼
ComfyUI        FastAPI Backend
      │              │
      └──────┬───────┘
             ▼
      Next.js Frontend
             │
             ▼
          Production Ready
```

---

# Deployment Script

Location

```bash
/home/pixelbloomco1/deploy.sh
```

```bash
#!/bin/bash
set -e

echo "======================================"
echo "Deploying ETSY Pipeline"
echo "======================================"

cd /home/pixelbloomco1/ETSY-pipeline

echo "Pull latest code..."
git pull origin main

echo "Updating Python packages..."
source venv/bin/activate
pip install -e .

echo "Building frontend..."
cd craftdesk_web
/home/pixelbloomco1/node-v20.11.0-linux-x64/bin/npm install
/home/pixelbloomco1/node-v20.11.0-linux-x64/bin/npm run build

echo "Restart backend..."
sudo systemctl restart backend

echo "Restart frontend..."
sudo systemctl restart frontend

echo "Deployment completed successfully."
```

Make executable

```bash
chmod +x ~/deploy.sh
```

Deploy

```bash
~/deploy.sh
```

---

# Production Workflow

### First Time Setup

```
Install Ubuntu

↓

Clone Repository

↓

Install Dependencies

↓

Create systemd Services

↓

Enable Services

↓

Build Frontend

↓

Start Services
```

### Daily Development

```
Local Development

↓

git push origin main

↓

SSH into VM

↓

~/deploy.sh

↓

Production Updated
```

### VM Restart

```
Start VM

↓

Ubuntu Boots

↓

systemd Starts

↓

Backend

↓

Frontend

↓

ComfyUI

↓

Ready
```

No manual commands are required after a VM reboot.