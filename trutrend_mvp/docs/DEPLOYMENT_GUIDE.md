# TrueTrend Diabetes Analytics Platform - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the TrueTrend Diabetes Analytics Platform in various environments, from local development to production-ready enterprise deployments.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Cloud Deployment Options](#cloud-deployment-options)
6. [Database Setup](#database-setup)
7. [Environment Configuration](#environment-configuration)
8. [Security Configuration](#security-configuration)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Backup and Recovery](#backup-and-recovery)

---

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB available space
- **OS**: Linux (Ubuntu 20.04+), macOS 10.15+, Windows 10

### Recommended Production Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 100GB+ SSD
- **OS**: Linux (Ubuntu 22.04 LTS)

### Software Dependencies
- **Python**: 3.11 or higher
- **PostgreSQL**: 12 or higher
- **Docker**: 20.10+ (optional but recommended)
- **Docker Compose**: 1.29+ (for multi-container deployments)

---

## Local Development Setup

### Option 1: Direct Python Installation

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/trutrend-mvp.git
cd trutrend-mvp
```

#### 2. Create Virtual Environment
```bash
# Using venv
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Using conda
conda create -n trutrend python=3.11
conda activate trutrend
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Set Up Environment Variables
```bash
cp .env.example .env
```

Edit `.env` file with your local configuration:
```bash
# Application
APP_NAME="TrueTrend Diabetes Analytics"
DEBUG=true

# Database (for local development)
DATABASE_URL=postgresql://postgres:password@localhost:5432/trutrend_dev

# Security (generate new keys for production)
SECRET_KEY=your-local-development-secret-key
ENCRYPTION_KEY=your-32-byte-development-encryption-key
```

#### 5. Set Up Local Database
```bash
# Install PostgreSQL locally or use Docker
docker run --name trutrend-postgres \
  -e POSTGRES_DB=trutrend_dev \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d postgres:15

# Wait for database to start
sleep 10

# Run database migrations (when available)
# alembic upgrade head
```

#### 6. Start Development Server
```bash
# Development server with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 7. Verify Installation
```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Access interactive documentation
open http://localhost:8000/docs
```

### Option 2: Using Docker Compose (Recommended)

#### 1. Clone and Start Services
```bash
git clone https://github.com/your-org/trutrend-mvp.git
cd trutrend-mvp

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up --build
```

#### 2. Verify Services
```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs trutrend-api
docker-compose logs postgres

# Test API
curl http://localhost:8000/api/v1/health
```

---

## Docker Deployment

### Single Container Deployment

#### 1. Build Image
```bash
# Build production image
docker build -t trutrend-mvp:latest .

# Or build with specific tag
docker build -t trutrend-mvp:v1.0.0 .
```

#### 2. Run Container
```bash
# Run with external database
docker run -d \
  --name trutrend-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@your-db-host:5432/trutrend" \
  -e SECRET_KEY="your-production-secret-key" \
  -e ENCRYPTION_KEY="your-32-byte-production-encryption-key" \
  -e DEBUG=false \
  -v /host/upload/path:/tmp/trutrend_uploads \
  trutrend-mvp:latest
```

### Multi-Container with Docker Compose

#### 1. Production Docker Compose
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trutrend_prod
      POSTGRES_USER: trutrend
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trutrend"]
      interval: 10s
      timeout: 5s
      retries: 5

  trutrend-api:
    image: trutrend-mvp:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://trutrend:${DB_PASSWORD}@postgres:5432/trutrend_prod
      - SECRET_KEY=${SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - DEBUG=false
      - AUDIT_LOGGING=true
      - ENCRYPTION_AT_REST=true
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./uploads:/tmp/trutrend_uploads
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - trutrend-api
    restart: unless-stopped

volumes:
  postgres_data:
```

#### 2. Deploy Production Stack
```bash
# Set environment variables
export DB_PASSWORD="your-secure-db-password"
export SECRET_KEY="your-production-secret-key"
export ENCRYPTION_KEY="your-32-byte-production-encryption-key"

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Check deployment
docker-compose -f docker-compose.prod.yml ps
```

---

## Production Deployment

### Prerequisites

#### 1. Server Setup (Ubuntu 22.04)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    curl \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Security Hardening
```bash
# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Configure fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Disable root SSH login
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

### Application Deployment

#### 1. Prepare Application Directory
```bash
# Create application directory
sudo mkdir -p /opt/trutrend
sudo chown $USER:$USER /opt/trutrend
cd /opt/trutrend

# Clone repository
git clone https://github.com/your-org/trutrend-mvp.git .

# Create required directories
mkdir -p uploads logs backups nginx/ssl
```

#### 2. Configure Environment
```bash
# Create production environment file
cp .env.example .env.prod
```

Edit `.env.prod`:
```bash
# Application
APP_NAME="TrueTrend Diabetes Analytics"
APP_VERSION="1.0.0"
DEBUG=false

# Database
DATABASE_URL=postgresql://trutrend:SECURE_PASSWORD@postgres:5432/trutrend_prod

# Security (CRITICAL: Generate new keys)
SECRET_KEY=GENERATE_SECURE_SECRET_KEY_HERE
ENCRYPTION_KEY=GENERATE_32_BYTE_ENCRYPTION_KEY_HERE

# File Upload
MAX_FILE_SIZE=52428800
UPLOAD_DIR=/tmp/trutrend_uploads

# Clinical Rules
POSTPRANDIAL_THRESHOLD=180.0
POSTPRANDIAL_WINDOW=120
MISTIMED_BOLUS_THRESHOLD=160.0
MISTIMED_BOLUS_DELAY=10

# Compliance
DATA_RETENTION_DAYS=2555
AUDIT_LOGGING=true
ENCRYPTION_AT_REST=true

# API Integration
GLOOKO_API_URL=https://api.glooko.com/v1
GLOOKO_API_KEY=YOUR_GLOOKO_API_KEY
```

#### 3. Generate Security Keys
```bash
# Generate secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### 4. Configure Nginx
Create `/opt/trutrend/nginx/nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream trutrend_api {
        server trutrend-api:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=1r/s;

    server {
        listen 80;
        server_name your-domain.com www.your-domain.com;
        
        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com www.your-domain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:50m;
        ssl_stapling on;
        ssl_stapling_verify on;
        
        # Security headers
        add_header Strict-Transport-Security "max-age=63072000" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        
        # API endpoints
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://trutrend_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Upload endpoints (stricter rate limiting)
        location /api/v1/upload-csv {
            limit_req zone=upload burst=5 nodelay;
            proxy_pass http://trutrend_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            client_max_body_size 50M;
        }

        # Health check
        location /api/v1/health {
            proxy_pass http://trutrend_api;
        }

        # Documentation
        location /docs {
            proxy_pass http://trutrend_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Root endpoint
        location / {
            proxy_pass http://trutrend_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

#### 5. SSL Certificate Setup
```bash
# Using Let's Encrypt
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Copy certificates to application directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/trutrend/nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/trutrend/nginx/ssl/
sudo chown $USER:$USER /opt/trutrend/nginx/ssl/*

# Set up automatic renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet && docker-compose -f /opt/trutrend/docker-compose.prod.yml restart nginx" | sudo crontab -
```

#### 6. Deploy Application
```bash
cd /opt/trutrend

# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check deployment
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs trutrend-api
```

#### 7. Verify Deployment
```bash
# Check health endpoint
curl https://your-domain.com/api/v1/health

# Check SSL rating
curl -I https://your-domain.com

# Test API functionality
curl -X POST "https://your-domain.com/api/v1/simulate-analytics/test_patient?user_role=patient"
```

---

## Cloud Deployment Options

### AWS Deployment

#### Using AWS ECS with Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker build -t trutrend-mvp .
docker tag trutrend-mvp:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/trutrend-mvp:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/trutrend-mvp:latest

# Deploy using AWS CLI or Terraform
```

#### ECS Task Definition Example
```json
{
  "family": "trutrend-mvp",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "trutrend-api",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/trutrend-mvp:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/trutrend"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:trutrend/secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/trutrend-mvp",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Platform

#### Using Cloud Run
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/trutrend-mvp

# Deploy to Cloud Run
gcloud run deploy trutrend-api \
  --image gcr.io/PROJECT_ID/trutrend-mvp \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL="postgresql://user:pass@cloud-sql-proxy:5432/trutrend" \
  --set-env-vars DEBUG=false \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10
```

### Azure Container Instances

```bash
# Create resource group
az group create --name trutrend-rg --location eastus

# Deploy container
az container create \
  --resource-group trutrend-rg \
  --name trutrend-api \
  --image your-registry/trutrend-mvp:latest \
  --cpu 1 \
  --memory 1 \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL="postgresql://user:pass@azure-postgres:5432/trutrend" \
    DEBUG=false
```

---

## Database Setup

### PostgreSQL Configuration

#### 1. Production Database Setup
```sql
-- Create database and user
CREATE DATABASE trutrend_prod;
CREATE USER trutrend WITH ENCRYPTED PASSWORD 'secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE trutrend_prod TO trutrend;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trutrend;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trutrend;

-- Configure for healthcare data
ALTER DATABASE trutrend_prod SET timezone TO 'UTC';
```

#### 2. Database Performance Tuning
```sql
-- Add to postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

#### 3. Backup Configuration
```bash
# Create backup script
cat > /opt/trutrend/scripts/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/trutrend/backups"
DB_NAME="trutrend_prod"
DB_USER="trutrend"

# Create encrypted backup
pg_dump -h postgres -U $DB_USER -d $DB_NAME | \
  gzip | \
  gpg --cipher-algo AES256 --compress-algo 1 --symmetric --output $BACKUP_DIR/backup_$DATE.sql.gz.gpg

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "backup_*.sql.gz.gpg" -mtime +30 -delete
EOF

chmod +x /opt/trutrend/scripts/backup.sh

# Schedule daily backups
echo "0 2 * * * /opt/trutrend/scripts/backup.sh" | crontab -
```

---

## Environment Configuration

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_NAME` | Application name | "TrueTrend Diabetes Analytics" | No |
| `APP_VERSION` | Application version | "1.0.0-MVP" | No |
| `DEBUG` | Enable debug mode | false | No |
| `DATABASE_URL` | PostgreSQL connection string | localhost | Yes |
| `SECRET_KEY` | Application secret key | N/A | Yes |
| `ENCRYPTION_KEY` | 32-byte encryption key | N/A | Yes |
| `MAX_FILE_SIZE` | Max upload size in bytes | 52428800 | No |
| `UPLOAD_DIR` | File upload directory | /tmp/trutrend_uploads | No |
| `POSTPRANDIAL_THRESHOLD` | Glucose threshold mg/dL | 180.0 | No |
| `POSTPRANDIAL_WINDOW` | Time window in minutes | 120 | No |
| `MISTIMED_BOLUS_THRESHOLD` | Glucose threshold mg/dL | 160.0 | No |
| `MISTIMED_BOLUS_DELAY` | Delay threshold in minutes | 10 | No |
| `DATA_RETENTION_DAYS` | Data retention period | 2555 | No |
| `AUDIT_LOGGING` | Enable audit logging | true | No |
| `ENCRYPTION_AT_REST` | Enable data encryption | true | No |
| `GLOOKO_API_URL` | Glooko API endpoint | https://api.glooko.com/v1 | No |
| `GLOOKO_API_KEY` | Glooko API key | N/A | No |

### Configuration Validation

Create validation script `/opt/trutrend/scripts/validate-config.sh`:
```bash
#!/bin/bash

echo "Validating TrueTrend configuration..."

# Check required environment variables
required_vars=("DATABASE_URL" "SECRET_KEY" "ENCRYPTION_KEY")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: $var is not set"
        exit 1
    fi
done

# Validate database connection
python3 -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('✓ Database connection successful')
    conn.close()
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
"

# Validate secret key length
python3 -c "
import os
key = os.environ.get('SECRET_KEY', '')
if len(key) < 32:
    print('✗ SECRET_KEY should be at least 32 characters')
    exit(1)
else:
    print('✓ SECRET_KEY length is adequate')
"

# Validate encryption key
python3 -c "
import os
from cryptography.fernet import Fernet
try:
    key = os.environ.get('ENCRYPTION_KEY', '').encode()
    Fernet(key)
    print('✓ ENCRYPTION_KEY is valid')
except Exception as e:
    print(f'✗ ENCRYPTION_KEY is invalid: {e}')
    exit(1)
"

echo "Configuration validation completed successfully!"
```

---

## Security Configuration

### HIPAA/GDPR Compliance Checklist

#### Data Protection
- [ ] All data encrypted at rest using AES-256
- [ ] Transport encryption using TLS 1.3
- [ ] Patient identifiers hashed in logs
- [ ] Secure key management implemented
- [ ] Data retention policies configured

#### Access Control
- [ ] Role-based access control (RBAC) implemented
- [ ] Strong authentication mechanisms
- [ ] Session management configured
- [ ] API rate limiting enabled
- [ ] Input validation on all endpoints

#### Audit and Monitoring
- [ ] Comprehensive audit logging
- [ ] Real-time monitoring configured
- [ ] Automated backup procedures
- [ ] Incident response plan documented
- [ ] Regular security assessments scheduled

#### Infrastructure Security
- [ ] Firewall configured
- [ ] Intrusion detection system active
- [ ] Regular security updates applied
- [ ] Vulnerability scanning enabled
- [ ] Network segmentation implemented

---

## Monitoring and Logging

### Application Monitoring

#### 1. Health Check Monitoring
```bash
# Create monitoring script
cat > /opt/trutrend/scripts/monitor.sh << 'EOF'
#!/bin/bash

HEALTH_URL="https://your-domain.com/api/v1/health"
ALERT_EMAIL="admin@your-domain.com"

response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $response -ne 200 ]; then
    echo "TrueTrend API health check failed - HTTP $response" | \
    mail -s "TrueTrend Alert: API Down" $ALERT_EMAIL
fi
EOF

# Schedule monitoring
echo "*/5 * * * * /opt/trutrend/scripts/monitor.sh" | crontab -
```

#### 2. Log Management
```yaml
# Add to docker-compose.prod.yml
version: '3.8'

services:
  trutrend-api:
    # ... existing configuration
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Add log aggregation service
  fluentd:
    image: fluent/fluentd:latest
    volumes:
      - ./logs:/fluentd/log
      - ./fluentd.conf:/fluentd/etc/fluent.conf
    ports:
      - "24224:24224"
```

### Performance Monitoring

#### 1. Application Metrics
```python
# Add to requirements.txt
prometheus-client==0.17.1

# Add metrics endpoint to main.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

#### 2. Database Monitoring
```sql
-- Create monitoring views
CREATE VIEW patient_data_stats AS
SELECT 
    COUNT(*) as total_patients,
    AVG(glucose_reading_count) as avg_readings_per_patient,
    MAX(last_upload) as latest_upload
FROM patient_summary;

-- Monitor query performance
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

---

## Backup and Recovery

### Backup Strategy

#### 1. Database Backups
```bash
# Full backup script
cat > /opt/trutrend/scripts/full-backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/trutrend/backups"
DATE=$(date +%Y%m%d_%H%M%S)
ENCRYPTION_PASSWORD="your-backup-encryption-password"

# Create full database backup
docker exec trutrend-postgres pg_dumpall -U postgres | \
  gzip | \
  gpg --batch --yes --passphrase "$ENCRYPTION_PASSWORD" \
    --cipher-algo AES256 --symmetric \
    --output "$BACKUP_DIR/full_backup_$DATE.sql.gz.gpg"

# Backup application data
tar -czf "$BACKUP_DIR/app_data_$DATE.tar.gz" \
  /opt/trutrend/uploads \
  /opt/trutrend/logs \
  /opt/trutrend/.env.prod

# Upload to remote storage (example: AWS S3)
aws s3 cp "$BACKUP_DIR/" s3://your-backup-bucket/trutrend/ --recursive

# Cleanup local backups older than 7 days
find "$BACKUP_DIR" -name "*.gpg" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
EOF
```

#### 2. Recovery Procedures
```bash
# Recovery script
cat > /opt/trutrend/scripts/restore.sh << 'EOF'
#!/bin/bash

BACKUP_FILE=$1
ENCRYPTION_PASSWORD="your-backup-encryption-password"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop application
docker-compose -f /opt/trutrend/docker-compose.prod.yml stop trutrend-api

# Restore database
gpg --batch --yes --passphrase "$ENCRYPTION_PASSWORD" \
  --decrypt "$BACKUP_FILE" | \
  gunzip | \
  docker exec -i trutrend-postgres psql -U postgres

# Restart application
docker-compose -f /opt/trutrend/docker-compose.prod.yml start trutrend-api

echo "Recovery completed. Please verify system functionality."
EOF
```

### Disaster Recovery Plan

#### 1. Recovery Time Objectives (RTO)
- **Critical System Failure**: 4 hours
- **Data Center Outage**: 8 hours
- **Regional Disaster**: 24 hours

#### 2. Recovery Point Objectives (RPO)
- **Database**: 15 minutes (continuous replication)
- **Application Data**: 1 hour (hourly snapshots)
- **Configuration**: 24 hours (daily backups)

#### 3. Recovery Procedures
1. **Assess the situation and activate disaster recovery team**
2. **Restore from most recent backup**
3. **Verify data integrity and system functionality**
4. **Update DNS records if necessary**
5. **Communicate status to stakeholders**
6. **Document incident and lessons learned**

---

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily
- [ ] Check system health and logs
- [ ] Verify backup completion
- [ ] Monitor disk space usage
- [ ] Review security alerts

#### Weekly
- [ ] Update system packages
- [ ] Review performance metrics
- [ ] Check certificate expiration dates
- [ ] Audit user access logs

#### Monthly
- [ ] Review and rotate logs
- [ ] Update application dependencies
- [ ] Test backup restoration procedures
- [ ] Conduct security vulnerability scans

#### Quarterly
- [ ] Review and update disaster recovery plan
- [ ] Conduct penetration testing
- [ ] Update documentation
- [ ] Review compliance requirements

### Update Procedures

#### 1. Application Updates
```bash
# Create update script
cat > /opt/trutrend/scripts/update.sh << 'EOF'
#!/bin/bash

echo "Starting TrueTrend update process..."

# Backup current version
/opt/trutrend/scripts/full-backup.sh

# Pull latest code
cd /opt/trutrend
git fetch origin
git checkout main
git pull origin main

# Build new image
docker build -t trutrend-mvp:latest .

# Update services with zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps trutrend-api

# Health check
sleep 30
if curl -f http://localhost:8000/api/v1/health; then
    echo "Update completed successfully"
else
    echo "Update failed, rolling back..."
    docker-compose -f docker-compose.prod.yml down
    # Restore from backup if necessary
    exit 1
fi
EOF
```

---

## Troubleshooting

### Common Issues

#### 1. Application Won't Start
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs trutrend-api

# Common causes:
# - Missing environment variables
# - Database connection issues
# - Port conflicts
# - Insufficient permissions
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
docker exec trutrend-postgres pg_isready -U postgres

# Check database logs
docker-compose -f docker-compose.prod.yml logs postgres

# Verify connection string in environment variables
```

#### 3. SSL Certificate Issues
```bash
# Check certificate expiration
openssl x509 -in /opt/trutrend/nginx/ssl/fullchain.pem -text -noout

# Renew Let's Encrypt certificate
sudo certbot renew

# Update certificate in Docker volume
sudo cp /etc/letsencrypt/live/your-domain.com/* /opt/trutrend/nginx/ssl/
```

#### 4. Performance Issues
```bash
# Check resource usage
docker stats

# Monitor database performance
docker exec trutrend-postgres psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Review application logs for errors
docker-compose -f docker-compose.prod.yml logs trutrend-api | grep ERROR
```

### Support Contacts

- **Technical Support**: support@trutrend.health
- **Security Issues**: security@trutrend.health
- **Emergency Contact**: +1-XXX-XXX-XXXX
- **Documentation**: https://docs.trutrend.health

---

*This deployment guide is regularly updated to reflect best practices and security requirements for healthcare applications. Last updated: 2024-01-01*