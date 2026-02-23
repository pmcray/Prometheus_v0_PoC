# Docker Deployment Guide

Quick guide to deploying Prometheus bots using Docker.

## Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed ([Get Docker Compose](https://docs.docker.com/compose/install/))
- Trained models in `models/` directory
- Bot accounts on OGS and/or Lichess

## Quick Start

### 1. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API tokens
nano .env
```

### 2. Build Images

```bash
# Build production image
docker build -f Dockerfile.production -t prometheus:latest .

# Or use docker-compose
docker-compose build
```

### 3. Deploy Bots

**Single Bot:**
```bash
# Deploy Go 9x9 bot
docker-compose up go-9x9-bot

# Or deploy Chess bot
docker-compose up chess-bot
```

**All Bots:**
```bash
# Deploy all bots in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all bots
docker-compose down
```

## Configuration

### docker-compose.yml

The compose file defines 4 services:

| Service | Description | Port |
|---------|-------------|------|
| `go-9x9-bot` | 9×9 Go bot on OGS | - |
| `go-19x19-bot` | 19×19 Go bot on OGS | - |
| `chess-bot` | Chess bot on Lichess | - |
| `dashboard` | Monitoring dashboard | 8050 |

### Customization

Edit `docker-compose.yml` to customize:

**MCTS Simulations:**
```yaml
command: >
  python scripts/deploy_ogs_bot.py
  --model models/go_9x9.h5
  --mcts-sims 800  # Increase for stronger play
```

**Time Controls:**
```yaml
command: >
  python scripts/deploy_lichess_bot.py
  --time-control bullet blitz rapid  # Add classical if desired
```

**Max Concurrent Games:**
```yaml
command: >
  python scripts/deploy_ogs_bot.py
  --max-games 10  # Increase if you have CPU/GPU power
```

## Management Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f go-9x9-bot

# Last 100 lines
docker-compose logs --tail=100
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart chess-bot
```

### Update Models

```bash
# Stop bots
docker-compose down

# Update models in models/ directory
cp new_model.h5 models/go_9x9.h5

# Restart bots
docker-compose up -d
```

### Resource Monitoring

```bash
# View resource usage
docker stats

# View specific container
docker stats prometheus-go-9x9
```

## Production Deployment

### Using systemd

Create `/etc/systemd/system/prometheus-bots.service`:

```ini
[Unit]
Description=Prometheus AI Bots
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/Prometheus_v0_PoC
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable prometheus-bots
sudo systemctl start prometheus-bots
```

### Using Kubernetes

For Kubernetes deployment:

1. Build and push image to registry
2. Create ConfigMaps for .env
3. Create Secrets for API tokens
4. Deploy using provided k8s manifests (coming soon)

## Troubleshooting

### Bot Not Connecting

**Check logs:**
```bash
docker-compose logs chess-bot
```

**Common issues:**
- Invalid API token in `.env`
- Model file not found
- Network connectivity

**Solution:**
```bash
# Restart with fresh logs
docker-compose restart chess-bot
docker-compose logs -f chess-bot
```

### High Memory Usage

**Check memory:**
```bash
docker stats prometheus-go-19x19
```

**Reduce MCTS simulations:**
```yaml
--mcts-sims 200  # Down from 800
```

**Or limit Docker memory:**
```yaml
services:
  go-19x19-bot:
    mem_limit: 2g
    memswap_limit: 2g
```

### Model Not Loading

**Verify model exists:**
```bash
docker-compose run go-9x9-bot ls -la models/
```

**Rebuild if needed:**
```bash
docker-compose build --no-cache go-9x9-bot
```

## Performance Optimization

### GPU Support

To enable GPU:

1. Install [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)

2. Add to `docker-compose.yml`:
```yaml
services:
  go-19x19-bot:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

3. Set environment:
```yaml
environment:
  - CUDA_VISIBLE_DEVICES=0
```

### CPU Optimization

**Multi-threaded MCTS:**
```yaml
environment:
  - OMP_NUM_THREADS=4
  - TF_NUM_INTRAOP_THREADS=4
  - TF_NUM_INTEROP_THREADS=2
```

### Network Optimization

**Use host network for lower latency:**
```yaml
services:
  chess-bot:
    network_mode: "host"
```

## Security Best Practices

1. **Never commit `.env`** - It contains secrets
2. **Use Docker secrets** in production:
   ```yaml
   secrets:
     ogs_token:
       file: ./secrets/ogs_token.txt
   ```
3. **Run as non-root user**:
   ```dockerfile
   USER 1000:1000
   ```
4. **Limit resources**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

## Monitoring

### Prometheus Metrics (coming soon)

Expose metrics endpoint:
```yaml
ports:
  - "9090:9090"
```

### Grafana Dashboard (coming soon)

Pre-built dashboard for:
- Games played
- Win rate
- Response time
- Resource usage

## Support

- **Issues**: https://github.com/pmcray/Prometheus_v0_PoC/issues
- **Docs**: See `notebooks/deployment_workshop.ipynb`
- **Community**: Coming soon

## Next Steps

1. ✅ Configure `.env` with your tokens
2. ✅ Place trained models in `models/`
3. ✅ Run `docker-compose up -d`
4. ✅ Monitor with `docker-compose logs -f`
5. ✅ Check bot performance on OGS/Lichess
6. 🔄 Iterate and improve!

---

**Happy deploying!** 🚀
