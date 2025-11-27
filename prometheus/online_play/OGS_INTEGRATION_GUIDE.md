# OGS (Online Go Server) Integration Guide

## Current Status

The OGS bot (`ogs.py`) is a **demo implementation** showing the structure and API. For production use, significant enhancements are needed.

### ✅ What's Implemented

- Basic class structure
- HTTP API client setup
- Challenge filtering logic
- Statistics tracking
- Basic game flow
- Thread management

### ⚠️ What's Missing for Production

1. **WebSocket/Socket.IO Connection**
   - OGS uses Socket.IO (not plain WebSocket)
   - Need proper Socket.IO client library
   - Event handling for real-time updates

2. **Authentication**
   - OAuth2 flow for secure authentication
   - Session management
   - Token refresh

3. **Game State Synchronization**
   - Real-time move updates via Socket.IO
   - SGF parsing and generation
   - Board state synchronization

4. **Protocol Implementation**
   - OGS-specific message format
   - Proper event handlers
   - Connection reconnection logic

---

## Production Implementation Options

### Option 1: Use Existing Bot Framework (Recommended)

Several Go bot frameworks exist that handle OGS integration:

**gtp2ogs** (Python)
```bash
# Install
pip install gtp2ogs

# Use with GTP-compatible engine
gtp2ogs --username your_bot --apikey YOUR_KEY --engine /path/to/engine
```

**Advantages**:
- Handles all protocol complexity
- Well-tested and maintained
- Just need to provide GTP-compatible engine

**Disadvantages**:
- Need to wrap Prometheus in GTP protocol

### Option 2: Implement from Scratch

If you need full control, here's what to implement:

#### Step 1: Install Socket.IO Client

```bash
pip install python-socketio[client]
```

#### Step 2: Implement Connection

```python
import socketio

sio = socketio.Client()

@sio.event
def connect():
    print('Connected to OGS')
    # Authenticate
    sio.emit('authenticate', {'token': api_token})

@sio.on('game/move')
def on_move(data):
    # Handle opponent's move
    game_id = data['game_id']
    move = data['move']
    # Update board and generate response

@sio.on('game/challenge')
def on_challenge(data):
    # Handle incoming challenge
    if should_accept(data):
        sio.emit('challenge/accept', {'id': data['id']})

# Connect
sio.connect('https://online-go.com/socket.io/')
```

#### Step 3: Implement OAuth2

```python
import requests
from requests_oauthlib import OAuth2Session

# OAuth2 endpoints
authorization_url = 'https://online-go.com/oauth2/authorize'
token_url = 'https://online-go.com/oauth2/token'

# Start OAuth2 flow
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri)
authorization_url, state = oauth.authorization_url(authorization_url)

# User visits authorization_url and grants access
# Redirect returns with authorization code

# Exchange code for token
token = oauth.fetch_token(
    token_url,
    authorization_response=callback_url,
    client_secret=client_secret
)

# Use token for authenticated requests
headers = {Authorization': f'Bearer {token["access_token"]}'}
```

#### Step 4: Implement SGF Handling

```python
def parse_sgf_move(sgf_string):
    """Parse SGF move notation."""
    # SGF format: ;B[pd] or ;W[dd]
    # Extract: color, coordinates
    pass

def generate_sgf_move(move, color):
    """Generate SGF move notation."""
    if move == ('pass',):
        return f';{color}[]'

    row, col = move
    col_letter = chr(ord('a') + col)
    row_letter = chr(ord('a') + row)
    return f';{color}[{col_letter}{row_letter}]'
```

#### Step 5: Game State Synchronization

```python
class OGSGameState:
    def __init__(self, game_data):
        self.game_id = game_data['id']
        self.board_size = game_data['width']
        self.moves = game_data['moves']

    def apply_move(self, move):
        """Apply move to local game state."""
        # Parse SGF move
        # Update local board
        # Detect captures
        pass

    def is_our_turn(self, our_color):
        """Check if it's our turn to move."""
        num_moves = len(self.moves)
        if our_color == 'black':
            return num_moves % 2 == 0
        else:
            return num_moves % 2 == 1
```

---

## Complete Example: Production OGS Bot

Here's a complete skeleton for a production bot:

```python
import socketio
import requests
from prometheus.models.go_models import PrometheusGoAgent
from prometheus.environments.go import GoEnvironment

class ProductionOGSBot:
    def __init__(self, username, api_token, agent):
        self.username = username
        self.api_token = api_token
        self.agent = agent

        # Socket.IO client
        self.sio = socketio.Client()
        self.setup_handlers()

        # Active games
        self.games = {}

    def setup_handlers(self):
        @self.sio.event
        def connect():
            print('Connected to OGS')
            self.authenticate()

        @self.sio.on('game/move')
        def on_move(data):
            self.handle_opponent_move(data)

        @self.sio.on('game/challenge')
        def on_challenge(data):
            self.handle_challenge(data)

        @self.sio.on('game/ended')
        def on_game_end(data):
            self.handle_game_end(data)

    def authenticate(self):
        """Authenticate with OGS servers."""
        self.sio.emit('authenticate', {
            'token': self.api_token
        })

    def start(self):
        """Start bot and connect to OGS."""
        self.sio.connect('https://online-go.com/socket.io/')
        self.sio.wait()

    def handle_challenge(self, data):
        """Handle incoming challenge."""
        # Check if we should accept
        if self.should_accept_challenge(data):
            self.sio.emit('challenge/accept', {'id': data['id']})

    def handle_opponent_move(self, data):
        """Handle opponent's move."""
        game_id = data['game_id']
        move_sgf = data['move']

        # Parse move
        move = self.parse_sgf_move(move_sgf)

        # Update game state
        if game_id not in self.games:
            self.games[game_id] = self.create_game_state(data)

        self.games[game_id].apply_move(move)

        # Generate our move
        if self.games[game_id].is_our_turn():
            our_move = self.get_ai_move(game_id)
            self.send_move(game_id, our_move)

    def get_ai_move(self, game_id):
        """Get move from AI agent."""
        game_state = self.games[game_id]
        env = game_state.to_environment()

        state = env.get_state()
        legal_moves = env.get_legal_moves()

        return self.agent.get_move(state, legal_moves, temperature=0.1)

    def send_move(self, game_id, move):
        """Send move to OGS."""
        move_sgf = self.generate_sgf_move(move)

        self.sio.emit('game/move', {
            'game_id': game_id,
            'move': move_sgf
        })

    def parse_sgf_move(self, sgf):
        """Parse SGF move string."""
        # Implementation here
        pass

    def generate_sgf_move(self, move):
        """Generate SGF move string."""
        # Implementation here
        pass
```

---

## Testing Without Full Implementation

You can test the bot logic without actual OGS connection:

```python
# Test with local games
from prometheus.training.go_training import play_match
from prometheus.models.go_models import PrometheusGoAgent, RandomGoAgent

# Create agents
prometheus_go = PrometheusGoAgent(board_size=19)
opponent = RandomGoAgent(board_size=19)

# Simulate online matches
results = play_match(
    agent1=prometheus_go,
    agent2=opponent,
    num_games=10,
    board_size=19,
    verbose=True
)

print(f"Simulated online performance: {results['agent1_win_rate']:.1%}")
```

---

## Alternative: REST API Polling (Simpler)

If real-time WebSocket is too complex, you can use REST API polling:

```python
class SimpleOGSBot:
    """Simpler OGS bot using REST API polling."""

    def __init__(self, api_token, agent):
        self.api_token = api_token
        self.agent = agent
        self.api_url = "https://online-go.com/api/v1"

    def poll_games(self):
        """Poll for active games."""
        response = requests.get(
            f"{self.api_url}/games",
            headers={'Authorization': f'Bearer {self.api_token}'}
        )
        return response.json()

    def get_game_state(self, game_id):
        """Get current game state."""
        response = requests.get(
            f"{self.api_url}/games/{game_id}",
            headers={'Authorization': f'Bearer {self.api_token}'}
        )
        return response.json()

    def submit_move(self, game_id, move):
        """Submit move via REST API."""
        response = requests.post(
            f"{self.api_url}/games/{game_id}/move",
            json={'move': move},
            headers={'Authorization': f'Bearer {self.api_token}'}
        )
        return response.status_code == 200

    def run(self):
        """Main loop - poll and respond."""
        while self.running:
            games = self.poll_games()

            for game in games:
                if game['player_to_move'] == self.user_id:
                    # It's our turn
                    state = self.get_game_state(game['id'])
                    move = self.get_ai_move(state)
                    self.submit_move(game['id'], move)

            time.sleep(5)  # Poll every 5 seconds
```

**Advantages**:
- Much simpler than WebSocket
- Easier to debug
- No need for Socket.IO

**Disadvantages**:
- Slower response time
- More API calls
- Not real-time

---

## Recommended Path Forward

### For Quick Demo (1-2 hours)
Use local `play_match()` to simulate online games and demonstrate capability.

### For Semi-Production (1-2 days)
Implement REST API polling bot - simpler but functional.

### For Full Production (1-2 weeks)
Implement full Socket.IO bot with OAuth2 and proper error handling.

### For Immediate Use (15 minutes)
Use existing bot framework like `gtp2ogs` with a GTP wrapper around Prometheus.

---

## GTP Wrapper for Prometheus

To use with existing bot frameworks, wrap Prometheus in GTP protocol:

```python
# gtp_wrapper.py
import sys
from prometheus.models.go_models import PrometheusGoAgent
from prometheus.environments.go import GoEnvironment

class PrometheusGTPWrapper:
    """GTP protocol wrapper for Prometheus Go agent."""

    def __init__(self, board_size=19):
        self.agent = PrometheusGoAgent(board_size=board_size)
        self.env = GoEnvironment(board_size=board_size)

    def handle_command(self, cmd):
        """Handle GTP command."""
        parts = cmd.strip().split()
        command = parts[0]

        if command == "genmove":
            color = parts[1]
            move = self.generate_move()
            return f"= {move}\\n\\n"

        elif command == "play":
            color = parts[1]
            move = parts[2]
            self.play_move(move)
            return "=\\n\\n"

        elif command == "boardsize":
            size = int(parts[1])
            return "=\\n\\n"

        elif command == "quit":
            sys.exit(0)

        return "?\\n\\n"

    def run(self):
        """Run GTP loop."""
        while True:
            try:
                line = input()
                response = self.handle_command(line)
                print(response, flush=True)
            except EOFError:
                break

if __name__ == "__main__":
    wrapper = PrometheusGTPWrapper()
    wrapper.run()
```

Then use with gtp2ogs:
```bash
gtp2ogs --username prometheus_bot --apikey YOUR_KEY --engine "python gtp_wrapper.py"
```

---

## Summary

| Approach | Time | Difficulty | Real-time | Recommended For |
|----------|------|------------|-----------|-----------------|
| Local simulation | 0h | Easy | N/A | Quick demo |
| REST polling | 1-2 days | Medium | No | Semi-production |
| Full Socket.IO | 1-2 weeks | Hard | Yes | Full production |
| GTP wrapper + existing bot | 1-2 hours | Easy | Yes | **Immediate use** ✅ |

**Recommendation**: Use GTP wrapper with `gtp2ogs` for fastest path to production OGS bot.
