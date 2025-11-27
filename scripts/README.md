# Deployment Scripts

This directory contains automated deployment scripts for running Prometheus agents on online gaming platforms.

## Available Scripts

### 1. Lichess Bot Deployment (`deploy_lichess_bot.py`)

Deploy chess agents to Lichess.org.

**Prerequisites:**
- Lichess BOT account (upgrade at [lichess.org/account/bot](https://lichess.org/account/bot))
- API token with `bot:play` scope from [lichess.org/account/oauth/token](https://lichess.org/account/oauth/token)
- Trained chess model (optional)

**Quick Start:**
```bash
# Set token as environment variable
export LICHESS_TOKEN="your_token_here"

# Deploy with default random agent
python scripts/deploy_lichess_bot.py

# Deploy with trained model
python scripts/deploy_lichess_bot.py --model models/chess_prometheus.h5

# Deploy Prometheus agent with online learning
python scripts/deploy_lichess_bot.py --agent prometheus

# Accept only blitz games
python scripts/deploy_lichess_bot.py --time blitz
```

**Options:**
- `--token TOKEN` - Lichess API token (or use LICHESS_TOKEN env var)
- `--model PATH` - Path to trained model (.h5 file)
- `--agent {prometheus,static}` - Agent type (default: prometheus)
- `--time {bullet,blitz,rapid,classical}` - Accepted time controls (can specify multiple)
- `--max-games N` - Maximum number of games to play

**Example with Full Options:**
```bash
python scripts/deploy_lichess_bot.py \
    --token lip_xxxxxxxxxxxx \
    --model models/chess_agent_gen50.h5 \
    --agent prometheus \
    --time blitz rapid \
    --max-games 100
```

---

### 2. OGS Bot Deployment (`deploy_ogs_bot.py`)

Deploy Go agents to Online Go Server (OGS).

**Prerequisites:**
- OGS account (create at [online-go.com](https://online-go.com/))
- Trained Go model (optional)
- For production: gtp2ogs bridge (see [OGS_INTEGRATION_GUIDE.md](../prometheus/online_play/OGS_INTEGRATION_GUIDE.md))

**Quick Start:**
```bash
# Set credentials as environment variables
export OGS_USERNAME="your_username"
export OGS_PASSWORD="your_password"

# Demo mode (test without connecting)
python scripts/deploy_ogs_bot.py --demo

# Deploy with default agent (requires connection)
python scripts/deploy_ogs_bot.py

# Deploy with MCTS enhancement
python scripts/deploy_ogs_bot.py --mcts --simulations 400

# Deploy with trained model
python scripts/deploy_ogs_bot.py --model models/go_SIZE.h5 --mcts
```

**Options:**
- `--username USER` - OGS username (or use OGS_USERNAME env var)
- `--password PASS` - OGS password (or use OGS_PASSWORD env var)
- `--model PATH` - Path to model (use SIZE placeholder for board size)
- `--agent {prometheus,static}` - Agent type (default: prometheus)
- `--sizes {9,13,19}` - Accepted board sizes (can specify multiple)
- `--mcts` - Enable MCTS enhancement (+300-500 ELO)
- `--simulations N` - MCTS simulations per move (default: 800)
- `--demo` - Demo mode (no actual connection)

**Example with Full Options:**
```bash
python scripts/deploy_ogs_bot.py \
    --username mybot \
    --password secretpass \
    --model models/go_SIZE_gen30.h5 \
    --agent prometheus \
    --sizes 9 13 \
    --mcts \
    --simulations 400
```

**Production Deployment:**

For production OGS deployment, the recommended approach is to use the **gtp2ogs bridge**:

1. Install gtp2ogs: https://github.com/online-go/gtp2ogs
2. Create GTP wrapper for your agent (see OGS_INTEGRATION_GUIDE.md)
3. Run: `gtp2ogs --username USER --password PASS -- python your_gtp_wrapper.py`

See the comprehensive guide: [prometheus/online_play/OGS_INTEGRATION_GUIDE.md](../prometheus/online_play/OGS_INTEGRATION_GUIDE.md)

---

## Training Models for Deployment

Before deployment, you should train your agents:

### Chess Training
```python
from prometheus.models.architectures import PrometheusChessAgent
from prometheus.training.chess_training import train_chess_agent

# Create and train agent
agent = PrometheusChessAgent()
trained_agent = train_chess_agent(
    agent,
    num_games=1000,
    save_path='models/chess_prometheus.h5'
)
```

### Go Training
```python
from prometheus.models.go_models import PrometheusGoAgent
from prometheus.training.go_training import train_go_agent

# Create and train agent
agent = PrometheusGoAgent(board_size=9)
trained_agent = train_go_agent(
    agent,
    num_games=500,
    save_path='models/go_9.h5'
)
```

---

## Monitoring Deployed Bots

### Lichess
- View bot profile: `https://lichess.org/@/YOUR_BOT_NAME`
- Watch games live: Bot games are publicly viewable
- Check rating: Visible on profile page

### OGS
- View bot profile: `https://online-go.com/player/YOUR_BOT_ID`
- Game history: Available on profile
- Rating: Displayed on profile

---

## Best Practices

1. **Start Small**
   - Test with `--demo` mode first
   - Play a few games manually before full deployment
   - Monitor initial games closely

2. **Choose Time Controls Wisely**
   - Faster agents (Random, Static) → bullet/blitz
   - MCTS agents → blitz/rapid (need time to think)
   - Prometheus agents → rapid/classical (online learning benefits from longer games)

3. **Model Management**
   - Save checkpoints during training
   - Test models offline before deployment
   - Keep backup of working models

4. **Graceful Shutdown**
   - Use Ctrl+C to stop bots cleanly
   - Bots will resign active games on shutdown
   - Ratings are updated even for resignations

5. **Resource Management**
   - MCTS is CPU-intensive (800 sims ≈ 5-10s per move)
   - Consider running on dedicated server for 24/7 uptime
   - Monitor memory usage for long-running bots

---

## Troubleshooting

### Lichess Bot Won't Start

**Problem:** "Error: Could not connect to Lichess"

**Solutions:**
1. Verify token has `bot:play` scope
2. Check account is upgraded to BOT status
3. Ensure token hasn't been revoked
4. Check internet connection

### OGS Connection Issues

**Problem:** "Error: Could not connect to OGS"

**Solutions:**
1. Verify credentials are correct
2. Check OGS server status
3. For production, use gtp2ogs bridge (more reliable)
4. Try demo mode first to test agent creation

### Bot Plays Poorly

**Problem:** Bot loses all games / makes random moves

**Solutions:**
1. Verify model loaded correctly (check path)
2. Ensure model was trained for correct board size
3. Consider enabling MCTS for stronger play
4. Check that model architecture matches agent type

### High CPU Usage

**Problem:** Bot uses too much CPU / times out

**Solutions:**
1. Reduce MCTS simulations (try 200-400 instead of 800)
2. Use Static agent instead of Prometheus (no online learning)
3. Accept slower time controls only
4. Run on more powerful hardware

---

## Architecture

```
scripts/
├── deploy_lichess_bot.py    # Chess bot deployment
├── deploy_ogs_bot.py         # Go bot deployment
└── README.md                 # This file

Depends on:
prometheus/
├── online_play/
│   ├── lichess.py           # Lichess API wrapper
│   └── ogs.py               # OGS API wrapper
├── models/
│   ├── architectures.py     # Chess agents
│   ├── go_models.py         # Go agents
│   └── go_mcts.py           # MCTS enhancement
└── environments/
    ├── chess.py             # Chess environment
    └── go.py                # Go environment
```

---

## Future Enhancements

Planned features for deployment scripts:

- [ ] Auto-accept challenges from specific rating ranges
- [ ] Opening book integration
- [ ] Game analysis and self-improvement
- [ ] Multi-account deployment
- [ ] Discord/Slack notifications
- [ ] Web dashboard for monitoring
- [ ] Automatic model updates
- [ ] Cloud deployment (AWS, GCP, Azure)

---

## Support

For issues with:
- **Lichess API:** https://lichess.org/api
- **OGS API:** https://ogs.docs.apiary.io/
- **Prometheus:** https://github.com/pmcray/Prometheus_v0_PoC/issues

---

## License

Same as main Prometheus project - see [LICENSE](../LICENSE)
