# ZECT — ECS/Fargate Deployment Configuration Guide

Complete guide to deploying ZECT as containers on AWS ECS with Fargate (serverless), Application Load Balancer, RDS PostgreSQL, and CI/CD pipeline.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         AWS Cloud                             │
│                                                              │
│  ┌─────────────┐    ┌────────────────────────────────────┐  │
│  │     ALB     │    │          ECS Cluster (Fargate)     │  │
│  │  :80/:443   │───▶│                                    │  │
│  └─────────────┘    │  ┌──────────┐   ┌──────────────┐  │  │
│                      │  │ Backend  │   │   Frontend   │  │  │
│                      │  │ Task:8000│   │  Task:80     │  │  │
│                      │  └────┬─────┘   └──────────────┘  │  │
│                      └───────┼───────────────────────────┘  │
│                              │                               │
│                      ┌───────▼───────┐                      │
│                      │   RDS (PG)    │                      │
│                      │   :5432       │                      │
│                      └───────────────┘                      │
│                                                              │
│  ┌─────────┐   ┌─────────┐   ┌────────────────┐           │
│  │   ECR   │   │  Secrets │   │  CloudWatch    │           │
│  │ Registry│   │  Manager │   │  Logs          │           │
│  └─────────┘   └─────────┘   └────────────────┘           │
└──────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- AWS CLI v2 configured (`aws configure`)
- Docker installed locally
- AWS account with ECS, ECR, RDS, ALB permissions
- Domain name (optional, for HTTPS)

---

## Step 1: Create ECR Repositories

```bash
# Create repositories for backend and frontend images
aws ecr create-repository --repository-name zect-backend --region us-east-1
aws ecr create-repository --repository-name zect-frontend --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

---

## Step 2: Create Dockerfiles

### Backend Dockerfile (`backend/Dockerfile`)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev)
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile (`frontend/Dockerfile`)

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Frontend Nginx Config (`frontend/nginx.conf`)

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (handled by ALB in production, this is fallback)
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Gzip compression
    gzip on;
    gzip_types text/css application/javascript application/json;
    gzip_min_length 1000;
}
```

---

## Step 3: Build and Push Docker Images

```bash
# Set variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1
export ECR_BASE=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_BASE

# Build and push backend
cd backend
docker build -t zect-backend .
docker tag zect-backend:latest $ECR_BASE/zect-backend:latest
docker push $ECR_BASE/zect-backend:latest

# Build and push frontend
cd ../frontend
docker build -t zect-frontend .
docker tag zect-frontend:latest $ECR_BASE/zect-frontend:latest
docker push $ECR_BASE/zect-frontend:latest
```

---

## Step 4: Create RDS PostgreSQL Instance

```bash
# Create DB subnet group (use your VPC subnets)
aws rds create-db-subnet-group \
  --db-subnet-group-name zect-db-subnet \
  --db-subnet-group-description "ZECT DB Subnets" \
  --subnet-ids subnet-xxxx subnet-yyyy

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier zect-production-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.4 \
  --master-username zect_admin \
  --master-user-password YourSecureRDSPassword123! \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-xxxxxxxx \
  --db-subnet-group-name zect-db-subnet \
  --db-name zect_db \
  --no-publicly-accessible \
  --backup-retention-period 7 \
  --multi-az
```

---

## Step 5: Store Secrets in AWS Secrets Manager

```bash
# Store database credentials
aws secretsmanager create-secret \
  --name zect/production/database \
  --secret-string '{
    "DATABASE_URL": "postgresql://zect_admin:YourSecureRDSPassword123!@zect-production-db.xxxxxxxx.us-east-1.rds.amazonaws.com:5432/zect_db"
  }'

# Store API keys
aws secretsmanager create-secret \
  --name zect/production/api-keys \
  --secret-string '{
    "GITHUB_TOKEN": "ghp_your_github_token",
    "OPENAI_API_KEY": "sk-your-openai-key"
  }'

# Store auth credentials
aws secretsmanager create-secret \
  --name zect/production/auth \
  --secret-string '{
    "ZECT_USERNAME": "admin@zinnia.com",
    "ZECT_PASSWORD": "YourSecurePassword!"
  }'
```

---

## Step 6: Create ECS Cluster and Task Definitions

### Create Cluster

```bash
aws ecs create-cluster --cluster-name zect-production
```

### Create Task Execution Role

```bash
# Create role
aws iam create-role \
  --role-name zect-ecs-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name zect-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Add Secrets Manager access
aws iam put-role-policy \
  --role-name zect-ecs-execution-role \
  --policy-name SecretsAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:zect/*"
    }]
  }'
```

### Backend Task Definition (`ecs/backend-task.json`)

```json
{
  "family": "zect-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/zect-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/zect-ecs-execution-role",
  "containerDefinitions": [
    {
      "name": "zect-backend",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/zect-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:zect/production/database:DATABASE_URL::"
        },
        {
          "name": "GITHUB_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:zect/production/api-keys:GITHUB_TOKEN::"
        },
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:zect/production/api-keys:OPENAI_API_KEY::"
        },
        {
          "name": "ZECT_USERNAME",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:zect/production/auth:ZECT_USERNAME::"
        },
        {
          "name": "ZECT_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:zect/production/auth:ZECT_PASSWORD::"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/zect-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

### Frontend Task Definition (`ecs/frontend-task.json`)

```json
{
  "family": "zect-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/zect-ecs-execution-role",
  "containerDefinitions": [
    {
      "name": "zect-frontend",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/zect-frontend:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/zect-frontend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:80/ || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

### Register Task Definitions

```bash
aws ecs register-task-definition --cli-input-json file://ecs/backend-task.json
aws ecs register-task-definition --cli-input-json file://ecs/frontend-task.json
```

---

## Step 7: Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name zect-alb \
  --subnets subnet-xxxx subnet-yyyy \
  --security-groups sg-xxxxxxxx \
  --scheme internet-facing \
  --type application

# Create target groups
aws elbv2 create-target-group \
  --name zect-backend-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxxxxx \
  --target-type ip \
  --health-check-path /health

aws elbv2 create-target-group \
  --name zect-frontend-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-xxxxxxxx \
  --target-type ip \
  --health-check-path /

# Create listener (HTTP)
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:<ACCOUNT_ID>:loadbalancer/app/zect-alb/xxxxxxxx \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<ACCOUNT_ID>:targetgroup/zect-frontend-tg/xxxxxxxx

# Add rule for API paths → backend
aws elbv2 create-rule \
  --listener-arn <LISTENER_ARN> \
  --conditions '[{"Field":"path-pattern","Values":["/api/*","/auth/*","/health"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"<BACKEND_TG_ARN>"}]' \
  --priority 10
```

---

## Step 8: Create ECS Services

```bash
# Create backend service
aws ecs create-service \
  --cluster zect-production \
  --service-name zect-backend \
  --task-definition zect-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxxx", "subnet-yyyy"],
      "securityGroups": ["sg-xxxxxxxx"],
      "assignPublicIp": "ENABLED"
    }
  }' \
  --load-balancers '[{
    "targetGroupArn": "<BACKEND_TG_ARN>",
    "containerName": "zect-backend",
    "containerPort": 8000
  }]'

# Create frontend service
aws ecs create-service \
  --cluster zect-production \
  --service-name zect-frontend \
  --task-definition zect-frontend \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxxx", "subnet-yyyy"],
      "securityGroups": ["sg-xxxxxxxx"],
      "assignPublicIp": "ENABLED"
    }
  }' \
  --load-balancers '[{
    "targetGroupArn": "<FRONTEND_TG_ARN>",
    "containerName": "zect-frontend",
    "containerPort": 80
  }]'
```

---

## Step 9: Auto-Scaling Configuration

```bash
# Register scalable targets
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/zect-production/zect-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Add scaling policy (CPU-based)
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/zect-production/zect-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name zect-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

---

## Step 10: CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy-ecs.yml`:

```yaml
name: Deploy to ECS

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_BACKEND: zect-backend
  ECR_FRONTEND: zect-frontend
  ECS_CLUSTER: zect-production

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build & push backend
        run: |
          cd backend
          docker build -t ${{ steps.ecr.outputs.registry }}/${{ env.ECR_BACKEND }}:${{ github.sha }} .
          docker push ${{ steps.ecr.outputs.registry }}/${{ env.ECR_BACKEND }}:${{ github.sha }}

      - name: Build & push frontend
        run: |
          cd frontend
          docker build -t ${{ steps.ecr.outputs.registry }}/${{ env.ECR_FRONTEND }}:${{ github.sha }} .
          docker push ${{ steps.ecr.outputs.registry }}/${{ env.ECR_FRONTEND }}:${{ github.sha }}

      - name: Update backend service
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service zect-backend \
            --force-new-deployment

      - name: Update frontend service
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service zect-frontend \
            --force-new-deployment
```

---

## Monitoring & Troubleshooting

### View Logs

```bash
# Backend logs
aws logs tail /ecs/zect-backend --follow

# Frontend logs
aws logs tail /ecs/zect-frontend --follow
```

### Check Service Status

```bash
aws ecs describe-services \
  --cluster zect-production \
  --services zect-backend zect-frontend \
  --query 'services[].{name:serviceName,status:status,running:runningCount,desired:desiredCount}'
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Task keeps restarting | Check CloudWatch logs, verify DATABASE_URL |
| 503 from ALB | Health check failing — check /health endpoint |
| Secrets not loading | Verify execution role has secretsmanager access |
| DB connection refused | Check security group allows ECS → RDS on port 5432 |

---

## Estimated Monthly Cost (AWS ECS/Fargate)

| Resource | Specification | Monthly Cost |
|----------|--------------|--------------|
| Fargate Backend (2 tasks) | 0.5 vCPU, 1GB each | ~$30 |
| Fargate Frontend (2 tasks) | 0.25 vCPU, 0.5GB each | ~$15 |
| ALB | Application Load Balancer | ~$22 |
| RDS db.t3.micro (Multi-AZ) | 1 vCPU, 1GB, 20GB | ~$28 |
| ECR | Image storage (~2GB) | ~$1 |
| CloudWatch Logs | ~5GB/month | ~$3 |
| Data Transfer | ~20GB/month | ~$2 |
| **Total** | | **~$101/month** |

---

## Comparison: EC2 vs ECS/Fargate

| Feature | EC2 | ECS/Fargate |
|---------|-----|-------------|
| **Cost** | ~$49/month | ~$101/month |
| **Scaling** | Manual / ASG | Automatic |
| **Maintenance** | OS patches, security | Zero server management |
| **Deployment** | SSH + scripts | Docker push + update |
| **High Availability** | Requires setup | Built-in (multi-AZ) |
| **Best For** | Dev/staging, small teams | Production, growing teams |

---

## Security Checklist (ECS)

- [ ] Secrets stored in AWS Secrets Manager (not env vars)
- [ ] RDS not publicly accessible
- [ ] Security groups: least privilege (ECS↔RDS only on 5432)
- [ ] ALB security group: only 80/443 inbound
- [ ] ECR image scanning enabled
- [ ] CloudWatch alarms for error rates
- [ ] VPC with private subnets for tasks (optional)
- [ ] WAF attached to ALB (optional, for DDoS protection)
- [ ] Enable container insights for monitoring
