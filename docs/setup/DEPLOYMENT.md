# LightRAG Production Deployment Guide

This guide covers production deployment scenarios for the LightRAG API system.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│   NGINX Gateway │────│   LightRAG API  │
│   (Optional)    │    │                 │    │   (Multiple)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                 │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │   External      │    │   Data Storage  │
│   Stack         │    │   Services      │    │   & Cache       │
│   - Prometheus  │    │   - Ollama      │    │   - RAG Data    │
│   - Grafana     │    │   - Qdrant      │    │   - Redis       │
│   - AlertMgr    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🐳 Docker Production Deployment

### Prerequisites

1. **Server Requirements**:
   - 16GB+ RAM
   - 8-24GB GPU VRAM (depending on model)
   - 100GB+ disk space
   - Docker 20.10+
   - Docker Compose 2.0+
   - NVIDIA Docker runtime

2. **Domain & SSL**:
   - Domain name configured
   - SSL certificates (Let's Encrypt recommended)
   - DNS records pointing to server

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Install NVIDIA Docker runtime
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 2: Production Configuration

```bash
# Clone repository
git clone <your-repo-url>
cd llm_backend

# Create production environment
cp .env.example .env.production

# Generate strong API keys
openssl rand -hex 32  # Generate secure API key

# Edit production configuration
vim .env.production
```

**Production .env.production**:
```bash
# Production API Configuration
RAG_API_HOST=0.0.0.0
RAG_API_PORT=8000
RAG_API_WORKERS=8
RAG_API_RELOAD=false
RAG_API_TITLE="LightRAG Production API"

# Security (CRITICAL)
RAG_API_KEY_ENABLED=true
RAG_API_KEYS=your-very-secure-api-key-generated-above
RAG_CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
RAG_MAX_REQUEST_SIZE=52428800  # 50MB
RAG_MAX_DOCUMENT_SIZE=10485760  # 10MB

# Model Configuration (Choose based on hardware)
RAG_LLM_MODEL=qwen2.5:32b-instruct-q4_K_M  # Production quality
RAG_EMBEDDING_MODEL=nomic-embed-text
RAG_LLM_TIMEOUT=600  # Longer timeout for production

# External Services (Use container names)
RAG_LLM_HOST=http://ollama:11434
RAG_QDRANT_HOST=http://qdrant:6333
RAG_REDIS_HOST=redis://redis:6379

# Performance Settings
RAG_ENABLE_CACHING=true
RAG_CACHE_TTL=7200  # 2 hours

# Rate Limiting (Adjust based on expected load)
RAG_RATE_LIMIT_REQUESTS=120  # requests per minute
RAG_RATE_LIMIT_WINDOW=60

# Logging
RAG_LOG_LEVEL=INFO
RAG_LOG_FORMAT=json
RAG_ENABLE_REQUEST_LOGGING=true
```

### Step 3: SSL Configuration

Create SSL certificate directory:
```bash
mkdir -p ssl
```

**Option A: Let's Encrypt (Recommended)**
```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/
sudo chown $USER:$USER ssl/*
```

**Option B: Self-signed (Development only)**
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem \
  -out ssl/fullchain.pem \
  -subj "/CN=yourdomain.com"
```

Update NGINX configuration:
```bash
# Edit configs/nginx/conf.d/api-gateway.conf
vim configs/nginx/conf.d/api-gateway.conf
```

**Production NGINX config**:
```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS configuration
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Proxy to API
    location /api/ {
        proxy_pass http://lightrag-api:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://lightrag-api:8000/health;
        access_log off;
    }
}
```

### Step 4: Production Docker Compose

Create `docker-compose.production.yml`:
```yaml
version: '3.8'

services:
  # LightRAG API Service
  lightrag-api:
    build: .
    deploy:
      replicas: 3  # Scale for production
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    environment:
      - RAG_LLM_HOST=http://ollama:11434
      - RAG_QDRANT_HOST=http://qdrant:6333
      - RAG_REDIS_HOST=redis://redis:6379
      - RAG_API_KEY_ENABLED=true
      - RAG_LOG_LEVEL=INFO
    env_file:
      - .env.production
    volumes:
      - ./rag_data:/app/rag_data
      - ./logs:/app/logs
    depends_on:
      - ollama
      - qdrant
      - redis
    restart: unless-stopped
    networks:
      - rag_network
    labels:
      - "prometheus.io/scrape=true"
      - "prometheus.io/port=8000"
      - "prometheus.io/path=/metrics"

  # Ollama with production settings
  ollama:
    image: ollama/ollama:latest
    container_name: rag_ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_NUM_PARALLEL=4
      - OLLAMA_MAX_LOADED_MODELS=2
    volumes:
      - ollama_models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - rag_network

  # Qdrant with persistent storage
  qdrant:
    image: qdrant/qdrant:v1.10.1
    container_name: rag_qdrant
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__STORAGE__PERFORMANCE__MAX_SEARCH_THREADS=8
    volumes:
      - qdrant_data:/qdrant/storage
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
    restart: unless-stopped
    networks:
      - rag_network

  # Redis with persistence
  redis:
    image: redis:7-alpine
    container_name: rag_redis
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 2G
    restart: unless-stopped
    networks:
      - rag_network

  # Prometheus for monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: rag_prometheus
    volumes:
      - ./configs/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--storage.tsdb.retention.size=10GB'
    restart: unless-stopped
    networks:
      - rag_network

  # Grafana with dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: rag_grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-changeme}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://yourdomain.com/grafana/
    volumes:
      - grafana_data:/var/lib/grafana
      - ./configs/grafana/provisioning:/etc/grafana/provisioning
      - ./configs/grafana/dashboards:/var/lib/grafana/dashboards
    restart: unless-stopped
    networks:
      - rag_network

  # NGINX with SSL
  nginx:
    image: nginx:alpine
    container_name: rag_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./configs/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./configs/nginx/conf.d:/etc/nginx/conf.d
      - ./ssl:/etc/nginx/ssl
    restart: unless-stopped
    networks:
      - rag_network
    depends_on:
      - lightrag-api

networks:
  rag_network:
    driver: bridge

volumes:
  ollama_models:
  qdrant_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

### Step 5: Deploy to Production

```bash
# Pull required models
docker-compose -f docker-compose.production.yml up -d ollama
sleep 30
docker exec rag_ollama ollama pull qwen2.5:32b-instruct-q4_K_M
docker exec rag_ollama ollama pull nomic-embed-text

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Verify deployment
curl -k https://yourdomain.com/api/health
```

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- NVIDIA GPU operator installed
- Ingress controller (NGINX recommended)
- Storage class for persistent volumes

### Step 1: Generate Kubernetes Manifests

```bash
# Install kompose
curl -L https://github.com/kubernetes/kompose/releases/latest/download/kompose-linux-amd64 -o kompose
chmod +x kompose
sudo mv kompose /usr/local/bin

# Generate manifests
kompose convert -f docker-compose.production.yml
```

### Step 2: Create Kubernetes Resources

**namespace.yaml**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lightrag-prod
```

**configmap.yaml**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lightrag-config
  namespace: lightrag-prod
data:
  RAG_API_HOST: "0.0.0.0"
  RAG_API_PORT: "8000"
  RAG_API_WORKERS: "8"
  RAG_LLM_MODEL: "qwen2.5:32b-instruct-q4_K_M"
  RAG_EMBEDDING_MODEL: "nomic-embed-text"
  RAG_LOG_LEVEL: "INFO"
  RAG_ENABLE_CACHING: "true"
```

**secret.yaml**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: lightrag-secrets
  namespace: lightrag-prod
type: Opaque
stringData:
  api-keys: "your-secure-api-key-here"
  grafana-password: "your-grafana-password"
```

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lightrag-api
  namespace: lightrag-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lightrag-api
  template:
    metadata:
      labels:
        app: lightrag-api
    spec:
      containers:
      - name: lightrag-api
        image: your-registry/lightrag-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: RAG_API_KEYS
          valueFrom:
            secretKeyRef:
              name: lightrag-secrets
              key: api-keys
        envFrom:
        - configMapRef:
            name: lightrag-config
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**ingress.yaml**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lightrag-ingress
  namespace: lightrag-prod
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - yourdomain.com
    secretName: lightrag-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: lightrag-api-service
            port:
              number: 8000
```

### Step 3: Deploy to Kubernetes

```bash
# Apply manifests
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Verify deployment
kubectl get pods -n lightrag-prod
kubectl get ingress -n lightrag-prod
```

## 🌩️ Cloud Deployment Options

### AWS ECS with Fargate

```yaml
# task-definition.json
{
  "family": "lightrag-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "lightrag-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/lightrag-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "RAG_LLM_HOST",
          "value": "https://api.ollama.com"
        }
      ],
      "secrets": [
        {
          "name": "RAG_API_KEYS",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:lightrag-api-keys"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/lightrag-api",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Run

```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: lightrag-api
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/execution-environment: gen2
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
      - image: gcr.io/project-id/lightrag-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: RAG_API_KEYS
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: keys
        resources:
          limits:
            cpu: 2000m
            memory: 8Gi
```

### Azure Container Instances

```yaml
# container-group.yaml
apiVersion: 2021-09-01
location: eastus
name: lightrag-api
properties:
  containers:
  - name: lightrag-api
    properties:
      image: your-registry.azurecr.io/lightrag-api:latest
      resources:
        requests:
          cpu: 2
          memoryInGb: 8
      ports:
      - port: 8000
        protocol: TCP
      environmentVariables:
      - name: RAG_LLM_HOST
        value: https://api.ollama.com
      - name: RAG_API_KEYS
        secureValue: your-secure-api-key
  osType: Linux
  ipAddress:
    type: Public
    ports:
    - protocol: tcp
      port: 8000
  restartPolicy: Always
```

## 📊 Production Monitoring Setup

### AlertManager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@yourdomain.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'admin@yourdomain.com'
    subject: 'LightRAG Alert: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

### Prometheus Rules

```yaml
# prometheus-rules.yml
groups:
- name: lightrag-api
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: High error rate detected
      description: Error rate is {{ $value }} errors per second

  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High latency detected
      description: 95th percentile latency is {{ $value }} seconds

  - alert: ServiceDown
    expr: up{job="lightrag-api"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: LightRAG API service is down
      description: The LightRAG API service has been down for more than 1 minute
```

## 🔧 Performance Tuning

### Resource Optimization

1. **CPU/Memory**:
   ```yaml
   # Kubernetes resource limits
   resources:
     requests:
       cpu: "1000m"
       memory: "4Gi"
     limits:
       cpu: "4000m"
       memory: "8Gi"
   ```

2. **GPU Configuration**:
   ```yaml
   # For NVIDIA GPUs
   resources:
     limits:
       nvidia.com/gpu: 1
   ```

### Database Tuning

1. **Qdrant Configuration**:
   ```yaml
   environment:
     - QDRANT__STORAGE__PERFORMANCE__MAX_SEARCH_THREADS=8
     - QDRANT__STORAGE__OPTIMIZERS__DEFAULT_SEGMENT_NUMBER=16
   ```

2. **Redis Configuration**:
   ```bash
   # Redis optimizations
   command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru --tcp-backlog 65536
   ```

### Load Balancing

```nginx
# NGINX upstream configuration
upstream lightrag_backend {
    least_conn;
    server lightrag-api-1:8000 max_fails=3 fail_timeout=30s;
    server lightrag-api-2:8000 max_fails=3 fail_timeout=30s;
    server lightrag-api-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    location /api/ {
        proxy_pass http://lightrag_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🔒 Security Hardening

### SSL/TLS Configuration

```nginx
# Strong SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# HSTS
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
```

### API Security

1. **Rate Limiting**: Configure per-API-key limits
2. **Request Size Limits**: Prevent large uploads
3. **Input Validation**: Validate all API inputs
4. **API Key Rotation**: Regular key rotation policy
5. **Audit Logging**: Log all API access attempts

### Container Security

```dockerfile
# Security improvements in Dockerfile
USER 1000:1000
COPY --chown=1000:1000 . /app
RUN chmod -R 755 /app
```

## 🚨 Disaster Recovery

### Backup Strategy

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)

# Backup RAG data
tar -czf "rag_data_backup_${DATE}.tar.gz" ./rag_data/

# Backup Redis
docker exec rag_redis redis-cli BGSAVE
docker cp rag_redis:/data/dump.rdb "redis_backup_${DATE}.rdb"

# Backup Qdrant
docker exec rag_qdrant tar -czf "/tmp/qdrant_backup_${DATE}.tar.gz" /qdrant/storage
docker cp "rag_qdrant:/tmp/qdrant_backup_${DATE}.tar.gz" .

# Upload to cloud storage
aws s3 cp "rag_data_backup_${DATE}.tar.gz" s3://your-backup-bucket/
aws s3 cp "redis_backup_${DATE}.rdb" s3://your-backup-bucket/
aws s3 cp "qdrant_backup_${DATE}.tar.gz" s3://your-backup-bucket/
```

### Recovery Procedures

```bash
#!/bin/bash
# restore.sh
BACKUP_DATE=$1

# Stop services
docker-compose down

# Restore RAG data
tar -xzf "rag_data_backup_${BACKUP_DATE}.tar.gz"

# Restore Redis
docker-compose up -d redis
docker cp "redis_backup_${BACKUP_DATE}.rdb" rag_redis:/data/dump.rdb
docker restart rag_redis

# Restore Qdrant
docker-compose up -d qdrant
docker exec rag_qdrant rm -rf /qdrant/storage/*
docker cp "qdrant_backup_${BACKUP_DATE}.tar.gz" rag_qdrant:/tmp/
docker exec rag_qdrant tar -xzf "/tmp/qdrant_backup_${BACKUP_DATE}.tar.gz" -C /

# Start all services
docker-compose up -d
```

## 📈 Scaling Strategies

### Horizontal Scaling

1. **Multiple API Instances**: Use load balancer
2. **Database Sharding**: Distribute data across instances
3. **Caching Layer**: Redis cluster for high availability
4. **CDN Integration**: Cache static responses

### Vertical Scaling

1. **GPU Scaling**: Multiple GPUs for model inference
2. **Memory Optimization**: Increase RAM for better caching
3. **CPU Optimization**: More cores for concurrent processing

### Auto-scaling

**Kubernetes HPA**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: lightrag-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: lightrag-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```
