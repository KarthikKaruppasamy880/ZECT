# ZECT — EC2 Deployment Configuration Guide

Complete guide to deploying ZECT on an AWS EC2 instance with PostgreSQL (RDS or local), Nginx reverse proxy, and systemd services.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   AWS EC2 Instance               │
│                                                  │
│  ┌─────────┐   ┌──────────┐   ┌─────────────┐  │
│  │  Nginx  │──▶│  Uvicorn │──▶│  PostgreSQL  │  │
│  │  :80/443│   │  :8000   │   │  (RDS/:5432) │  │
│  └─────────┘   └──────────┘   └─────────────┘  │
│       │                                          │
│       ▼                                          │
│  ┌──────────────┐                               │
│  │  Vite Build  │                               │
│  │  (Static)    │                               │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

---

## Prerequisites

- AWS Account with EC2 access
- Domain name (optional, for HTTPS)
- SSH key pair for EC2 access
- PostgreSQL database (RDS recommended for production)

---

## Step 1: Launch EC2 Instance

### Recommended Instance Configuration

| Setting | Value |
|---------|-------|
| AMI | Ubuntu 24.04 LTS |
| Instance Type | t3.medium (2 vCPU, 4GB RAM) |
| Storage | 30 GB gp3 |
| Security Group | Ports 22, 80, 443, 8000 |

### Security Group Rules

```
Inbound:
- SSH (22)        → Your IP only
- HTTP (80)       → 0.0.0.0/0
- HTTPS (443)     → 0.0.0.0/0
- Custom (8000)   → 0.0.0.0/0 (API, can restrict later)

Outbound:
- All traffic     → 0.0.0.0/0
```

### Launch via AWS CLI

```bash
aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxx \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=zect-server}]'
```

---

## Step 2: Connect and Install Dependencies

```bash
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install Nginx
sudo apt install -y nginx

# Install PostgreSQL client (for psql commands)
sudo apt install -y postgresql-client

# Verify installations
python3 --version   # 3.12+
node --version      # 20+
poetry --version    # 2.x
nginx -v            # 1.x
```

---

## Step 3: Clone and Configure ZECT

```bash
# Clone repo
cd /home/ubuntu
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT

# Checkout the production branch
git checkout main
```

---

## Step 4: Set Up PostgreSQL (RDS)

### Option A: AWS RDS PostgreSQL (Recommended)

```bash
aws rds create-db-instance \
  --db-instance-identifier zect-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.4 \
  --master-username zect_admin \
  --master-user-password YourSecurePassword123! \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-xxxxxxxx \
  --db-name zect_db \
  --publicly-accessible \
  --backup-retention-period 7
```

Wait for the instance to be available, then get the endpoint:
```bash
aws rds describe-db-instances --db-instance-identifier zect-db \
  --query 'DBInstances[0].Endpoint.Address' --output text
```

### Option B: Local PostgreSQL on EC2

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

sudo -u postgres psql -c "CREATE DATABASE zect_db;"
sudo -u postgres psql -c "CREATE USER zect_user WITH PASSWORD 'ZectSecure2026!';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE zect_db TO zect_user;"
sudo -u postgres psql -c "ALTER DATABASE zect_db OWNER TO zect_user;"
```

---

## Step 5: Configure Backend

```bash
cd /home/ubuntu/ZECT/backend

# Install dependencies
poetry install --no-dev

# Create .env file
cat > .env << 'EOF'
# Database — use RDS endpoint or localhost
DATABASE_URL=postgresql://zect_admin:YourSecurePassword123!@zect-db.xxxxxxxx.us-east-1.rds.amazonaws.com:5432/zect_db

# GitHub Integration
GITHUB_TOKEN=ghp_your_github_pat_here

# OpenAI for AI features (Ask, Plan, Blueprint, Code Review)
OPENAI_API_KEY=sk-your-openai-key-here

# Authentication
ZECT_USERNAME=your-admin-email@company.com
ZECT_PASSWORD=YourSecurePassword!

# Production settings
ENVIRONMENT=production
EOF

chmod 600 .env
```

---

## Step 6: Build Frontend

```bash
cd /home/ubuntu/ZECT/frontend

# Install dependencies
npm install

# Build for production
npm run build

# Output goes to /home/ubuntu/ZECT/frontend/dist/
```

---

## Step 7: Create Systemd Service (Backend)

```bash
sudo tee /etc/systemd/system/zect-backend.service << 'EOF'
[Unit]
Description=ZECT Backend API Server
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ZECT/backend
Environment=PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/.local/bin/poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable zect-backend
sudo systemctl start zect-backend

# Check status
sudo systemctl status zect-backend
```

---

## Step 8: Configure Nginx

```bash
sudo tee /etc/nginx/sites-available/zect << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or EC2 public IP

    # Frontend (static files)
    location / {
        root /home/ubuntu/ZECT/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Auth endpoint
    location /auth/ {
        proxy_pass http://127.0.0.1:8000/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
EOF

# Enable site and remove default
sudo ln -sf /etc/nginx/sites-available/zect /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 9: Add HTTPS with Let's Encrypt (Optional)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo systemctl reload nginx

# Auto-renew certificate
sudo crontab -e
# Add: 0 0 1 * * certbot renew --quiet
```

---

## Step 10: Verify Deployment

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl -I http://localhost

# Check logs
sudo journalctl -u zect-backend -f

# Check database connection
cd /home/ubuntu/ZECT/backend
poetry run python -c "from app.database import engine; print('DB connected:', engine.url)"
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `GITHUB_TOKEN` | Yes | GitHub PAT for repo access |
| `OPENAI_API_KEY` | Yes | OpenAI API key for AI features |
| `ZECT_USERNAME` | Yes | Login email |
| `ZECT_PASSWORD` | Yes | Login password |
| `ENVIRONMENT` | No | `production` or `development` |

---

## Updating the Deployment

```bash
cd /home/ubuntu/ZECT
git pull origin main

# Rebuild frontend
cd frontend && npm install && npm run build

# Restart backend
sudo systemctl restart zect-backend

# Verify
sudo systemctl status zect-backend
curl http://localhost:8000/health
```

---

## Monitoring & Logs

```bash
# Backend logs
sudo journalctl -u zect-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# System resources
htop
```

---

## Estimated Monthly Cost (AWS)

| Resource | Specification | Monthly Cost |
|----------|--------------|--------------|
| EC2 t3.medium | 2 vCPU, 4GB RAM | ~$30 |
| RDS db.t3.micro | 1 vCPU, 1GB RAM, 20GB | ~$15 |
| EBS 30GB gp3 | Storage | ~$3 |
| Data Transfer | ~10GB/month | ~$1 |
| **Total** | | **~$49/month** |

---

## Security Checklist

- [ ] SSH key-only access (disable password auth)
- [ ] Security group restricts SSH to your IP
- [ ] `.env` file has `chmod 600` permissions
- [ ] HTTPS enabled with valid certificate
- [ ] RDS not publicly accessible (same VPC as EC2)
- [ ] Regular OS updates (`apt upgrade`)
- [ ] Database backups enabled (RDS automated)
- [ ] No secrets in git repository
- [ ] Firewall (UFW) configured
