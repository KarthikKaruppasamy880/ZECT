# ZECT AWS Deployment Guide

> Step-by-step instructions for deploying ZECT to Amazon Web Services.

---

## Architecture Overview

```
                    ┌─────────────────┐
                    │   Route 53 DNS  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  ALB / CloudFront│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │                             │
     ┌────────▼────────┐          ┌────────▼────────┐
     │  Frontend (S3 + │          │  Backend (ECS   │
     │  CloudFront)    │          │  Fargate / EC2) │
     └─────────────────┘          └────────┬────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  RDS / SQLite   │
                                  │  (EBS Volume)   │
                                  └─────────────────┘
```

---

## Option 1: EC2 Single Instance (Simplest)

Best for: Small teams, proof-of-concept, cost-conscious deployments.

### Prerequisites
- AWS account with EC2 access
- SSH key pair created in your region
- Security group allowing ports 22, 80, 443

### Step 1: Launch EC2 Instance

```bash
# Launch Ubuntu 22.04 LTS, t3.small (2 vCPU, 2 GB RAM)
aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --instance-type t3.small \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=zect-server}]' \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20}}]'
```

### Step 2: SSH and Install Dependencies

```bash
ssh -i your-key.pem ubuntu@<public-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3.11+ and Poetry
sudo apt install -y python3.11 python3.11-venv python3-pip
pip3 install poetry

# Install Nginx (reverse proxy)
sudo apt install -y nginx
```

### Step 3: Clone and Build

```bash
# Clone the repository
git clone https://github.com/KarthikKaruppasamy880/ZECT.git
cd ZECT

# Backend setup
cd backend
poetry install --no-dev
cp .env.example .env

# Frontend setup
cd ../frontend
npm install
npm run build
```

### Step 4: Configure Environment Variables

Edit `/home/ubuntu/ZECT/backend/.env`:

```env
# Required
ZECT_USERNAME=admin
ZECT_PASSWORD=your-secure-password

# Optional - GitHub API (for repo analysis)
GITHUB_TOKEN=ghp_your_token_here

# Optional - OpenAI (for Ask/Plan/Blueprint AI)
OPENAI_API_KEY=sk-your-key-here

# Database (SQLite default, or PostgreSQL)
DATABASE_URL=sqlite:////data/app.db
```

### Step 5: Configure Nginx

```nginx
# /etc/nginx/sites-available/zect
server {
    listen 80;
    server_name your-domain.com;

    # Frontend (built static files)
    location / {
        root /home/ubuntu/ZECT/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /healthz {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/zect /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

### Step 6: Create Systemd Service

```ini
# /etc/systemd/system/zect-backend.service
[Unit]
Description=ZECT Backend API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ZECT/backend
Environment=PATH=/home/ubuntu/.local/bin:/usr/bin
EnvironmentFile=/home/ubuntu/ZECT/backend/.env
ExecStart=/home/ubuntu/.local/bin/poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable zect-backend
sudo systemctl start zect-backend
```

### Step 7: Add SSL with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Option 2: ECS Fargate (Production-Grade)

Best for: Production deployments, auto-scaling, zero-downtime updates.

### Prerequisites
- AWS CLI configured
- Docker installed locally
- ECR repository created

### Step 1: Create Docker Images

**Backend Dockerfile** (`backend/Dockerfile`):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-dev
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile** (`frontend/Dockerfile`):
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Step 2: Push to ECR

```bash
# Create repositories
aws ecr create-repository --repository-name zect-backend
aws ecr create-repository --repository-name zect-frontend

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t zect-backend ./backend
docker tag zect-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/zect-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/zect-backend:latest

docker build -t zect-frontend ./frontend \
  --build-arg VITE_API_URL=https://api.your-domain.com
docker tag zect-frontend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/zect-frontend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/zect-frontend:latest
```

### Step 3: Create ECS Cluster and Services

```bash
# Create cluster
aws ecs create-cluster --cluster-name zect-cluster

# Create task definitions (see task-definition.json below)
aws ecs register-task-definition --cli-input-json file://backend-task-def.json
aws ecs register-task-definition --cli-input-json file://frontend-task-def.json

# Create services
aws ecs create-service \
  --cluster zect-cluster \
  --service-name zect-backend \
  --task-definition zect-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### Step 4: Configure ALB

1. Create an Application Load Balancer
2. Add target groups for backend (port 8000) and frontend (port 80)
3. Configure routing rules:
   - `/api/*` -> backend target group
   - `/*` -> frontend target group

---

## Option 3: S3 + Lambda (Serverless)

Best for: Minimal cost, auto-scaling, no server management.

### Frontend: S3 + CloudFront

```bash
# Create S3 bucket for frontend
aws s3 mb s3://zect-frontend-<unique-id>

# Build and deploy frontend
cd frontend
VITE_API_URL=https://api.your-domain.com npm run build
aws s3 sync dist/ s3://zect-frontend-<unique-id> --delete

# Create CloudFront distribution pointing to S3 bucket
aws cloudfront create-distribution \
  --origin-domain-name zect-frontend-<unique-id>.s3.amazonaws.com \
  --default-root-object index.html
```

### Backend: Lambda + API Gateway

Use [Mangum](https://mangum.io/) to wrap the FastAPI app for Lambda:

```python
# backend/lambda_handler.py
from mangum import Mangum
from app.main import app

handler = Mangum(app)
```

```bash
pip install mangum
# Package and deploy using SAM or CDK
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZECT_USERNAME` | Yes | (none) | Login username |
| `ZECT_PASSWORD` | Yes | (none) | Login password |
| `GITHUB_TOKEN` | No | (none) | GitHub PAT for repo analysis (5000 req/hr) |
| `OPENAI_API_KEY` | No | (none) | OpenAI key for Ask/Plan/Blueprint AI |
| `DATABASE_URL` | No | `sqlite:///./zect.db` | Database connection string |
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API URL (frontend build-time) |

---

## Database Options

### SQLite (Default)
- Zero configuration, file-based
- Good for single-instance deployments
- Data stored at `/data/app.db` (Docker) or `./zect.db` (local)

### PostgreSQL (Production)
```env
DATABASE_URL=postgresql://user:password@hostname:5432/zect
```

Create an RDS instance:
```bash
aws rds create-db-instance \
  --db-instance-identifier zect-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username zectadmin \
  --master-user-password your-secure-password \
  --allocated-storage 20
```

---

## Monitoring

### CloudWatch
```bash
# Create log group
aws logs create-log-group --log-group-name /ecs/zect-backend

# Set up alarms
aws cloudwatch put-metric-alarm \
  --alarm-name zect-cpu-high \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### Health Check
ZECT exposes `GET /healthz` which returns `{"status": "ok"}`. Use this for:
- ALB health checks
- Route 53 health checks
- Uptime monitoring (e.g., AWS Health Dashboard)

---

## Cost Estimates

| Deployment Option | Monthly Cost (est.) |
|-------------------|-------------------|
| EC2 t3.small + RDS | ~$25-35/mo |
| ECS Fargate (2 tasks) | ~$40-60/mo |
| S3 + Lambda | ~$5-15/mo (usage-based) |

---

## Security Checklist

- [ ] Enable HTTPS/TLS (Let's Encrypt or ACM)
- [ ] Set strong ZECT_USERNAME and ZECT_PASSWORD
- [ ] Store secrets in AWS Secrets Manager or Parameter Store
- [ ] Restrict security groups to necessary ports only
- [ ] Enable CloudTrail for audit logging
- [ ] Set up WAF rules for API protection
- [ ] Enable automated backups for database
- [ ] Rotate GitHub and OpenAI API keys periodically
