# SurfScreen Deployment Guide

This guide covers deploying SurfScreen in production environments.

## Quick Start (Docker)

```bash
# Clone repository
git clone https://github.com/your-org/surfscreen.git
cd surfscreen

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start services
docker-compose up -d
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│   API Server    │
│  (Next.js)      │     │   (FastAPI)     │
│  Port: 3000     │     │   Port: 8000    │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │     Redis       │
                        │   (Job Queue)   │
                        │   Port: 6379    │
                        └─────────────────┘
```

## Environment Variables

| Variable             | Description            | Default               |
| -------------------- | ---------------------- | --------------------- |
| `SURFSCREEN_API_KEY` | API authentication key | Required              |
| `API_PORT`           | API server port        | 8000                  |
| `DASHBOARD_PORT`     | Dashboard port         | 3000                  |
| `CORS_ORIGINS`       | Allowed CORS origins   | http://localhost:3000 |
| `LOG_LEVEL`          | Logging level          | INFO                  |
| `DEFAULT_ENGINE`     | Default calculator     | emt                   |
| `DEFAULT_DEVICE`     | Default device         | cpu                   |

## Docker Deployment

### Build Images

```bash
# Build API image
docker build -f Dockerfile.api -t surfscreen-api .

# Build Dashboard image
docker build -f Dockerfile.dashboard -t surfscreen-dashboard ./dashboard
```

### Run with Docker Compose

```bash
# Production
docker-compose up -d

# Development (with hot reload)
docker-compose -f docker-compose.dev.yml up

# View logs
docker-compose logs -f api
docker-compose logs -f dashboard

# Stop services
docker-compose down
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Dashboard
curl http://localhost:3000
```

## Kubernetes Deployment

### Basic Deployment

```yaml
# surfscreen-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: surfscreen-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: surfscreen-api
  template:
    metadata:
      labels:
        app: surfscreen-api
    spec:
      containers:
        - name: api
          image: surfscreen-api:latest
          ports:
            - containerPort: 8000
          env:
            - name: SURFSCREEN_API_KEY
              valueFrom:
                secretKeyRef:
                  name: surfscreen-secrets
                  key: api-key
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: surfscreen-api
spec:
  selector:
    app: surfscreen-api
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

Apply with:

```bash
kubectl apply -f surfscreen-deployment.yaml
```

## GPU Support

For MACE with GPU acceleration:

```yaml
# docker-compose.gpu.yml
services:
  api:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - DEFAULT_DEVICE=cuda
```

Run with:

```bash
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

## Scaling

### Horizontal Scaling

```bash
# Scale API replicas
docker-compose up -d --scale api=3
```

### Load Balancer (nginx)

```nginx
upstream surfscreen_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;

    location /api {
        proxy_pass http://surfscreen_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://dashboard:3000;
    }
}
```

## Backup and Recovery

### Backup Results

```bash
# Backup results volume
docker run --rm -v surfscreen-results:/data -v $(pwd):/backup \
    alpine tar czf /backup/results-backup.tar.gz -C /data .
```

### Restore Results

```bash
# Restore from backup
docker run --rm -v surfscreen-results:/data -v $(pwd):/backup \
    alpine tar xzf /backup/results-backup.tar.gz -C /data
```

## Monitoring

### Prometheus Metrics

Add to API for metrics endpoint:

```python
from prometheus_client import Counter, Histogram
```

### Logging

Logs are available via:

```bash
docker-compose logs -f --tail=100 api
```

## Security Checklist

- [ ] Change default API key
- [ ] Enable HTTPS in production
- [ ] Restrict CORS origins
- [ ] Use secrets management for credentials
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Regular security updates

## Troubleshooting

### API not starting

```bash
# Check logs
docker-compose logs api

# Verify environment
docker-compose exec api env | grep SURFSCREEN
```

### Dashboard connection issues

```bash
# Verify API is reachable from dashboard container
docker-compose exec dashboard wget -qO- http://api:8000/health
```

### Redis connection issues

```bash
# Check Redis
docker-compose exec redis redis-cli ping
```
