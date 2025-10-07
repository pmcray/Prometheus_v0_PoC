# Prometheus v0.75 Implementation Roadmap

**Version:** v0.75 - "Foundational Refactor for Gaming & Edge AI"
**Target Platform:** NVIDIA Jetson Orin Nano 8GB
**Date Created:** 2025-10-06
**Status:** 🚀 Ready to Begin

---

## 📋 Executive Summary

v0.75 represents a **strategic pivot** from cloud-based code refactoring to **game-playing AI on edge hardware**. This is a complete architectural reboot with:

- **Platform:** Jetson Orin Nano (8GB RAM, 40 TOPS INT8)
- **Model:** Microsoft Phi-3-mini-4k-instruct (4-bit quantized)
- **Inference:** oLLM (SSD-offloaded for low VRAM)
- **Task Domain:** Turn-based strategy games (Connect 4, Chess)
- **Goal:** Prove CAM architecture works on resource-constrained edge hardware

**Key Insight:** Slow inference (several seconds) is acceptable for turn-based games where it appears as "thinking time."

---

## 🎯 Version Objectives

### Primary Goal
Establish a **stable, performant foundation** on Jetson hardware with real-time game visualization.

### Success Criteria
✅ Play a full, legal game of Connect 4
✅ Real-time pygame visualization updates
✅ CAM agents communicate via JSON protocol
✅ System runs entirely on Jetson (no cloud dependencies)

### NOT Required in v0.75
❌ Learning/improvement (comes in v0.80)
❌ Strategic play (random/simple moves OK)
❌ Winning games

---

## 📦 Prerequisites & Hardware

### Hardware Required
- **NVIDIA Jetson Orin Nano 8GB Developer Kit**
  - 1024-core Ampere GPU with 32 Tensor Cores
  - 40 TOPS INT8 AI performance
  - 8GB LPDDR5 RAM (shared CPU/GPU)
  - NVMe SSD for model offloading
  - Already available at `/home/pmc/`

### Software Stack
```bash
# Base System
- Ubuntu 20.04 (JetPack SDK)
- Python 3.8+
- Docker with NVIDIA runtime

# Python Libraries
- oLLM (for local LLM serving)
- pygame (game visualization)
- numpy, pydantic (data structures)
- pytest (testing)

# Foundation Model
- Microsoft Phi-3-mini-4k-instruct (4-bit IQ4_XS quantized)
- Size: ~2.3GB quantized
```

---

## 🏗️ Architecture Overview

### Causal Agentic Mesh (CAM) v0.2

```
User Goal → [StrategyAgent] → [MoveGeneratorAgent] → [EvaluatorAgent]
                                      ↓
                              [oLLM Server (Phi-3)]
                                      ↓
                              [Validation & Display]
```

#### Agent Responsibilities

1. **StrategyAgent**
   - Task dispatcher (simplified for v0.75)
   - Sends: "Given board state, generate next valid move"

2. **MoveGeneratorAgent**
   - Interfaces with local LLM via oLLM
   - Formats board state into structured prompt
   - Parses LLM response into move notation

3. **EvaluatorAgent**
   - Rules engine for move validation
   - Checks if move is legal
   - Rejects illegal moves (triggers retry)

### Communication Protocol
- **Format:** JSON schema-validated messages
- **Validation:** Pydantic models
- **Error Handling:** Retry loop for malformed JSON
- **Example:**
  ```json
  {
    "message_type": "move_request",
    "board_state": [[0, 0, 0, 0, 0, 0, 0], ...],
    "player": 1,
    "legal_moves": [0, 1, 2, 3, 4, 5, 6]
  }
  ```

---

## 📅 Implementation Plan

### Phase 1: Environment Setup (Week 1)

#### Task 1.1: Jetson Hardware Configuration
**Estimated Time:** 2-4 hours

```bash
# 1. Flash JetPack SDK
sudo apt update
sudo apt install nvidia-jetpack

# 2. Enable maximum performance mode
sudo nvpmodel -m 2  # 67 TOPS mode
sudo jetson_clocks   # Lock clocks to max

# 3. Verify GPU availability
nvidia-smi

# 4. Install Docker with NVIDIA runtime
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install -y nvidia-docker2
sudo systemctl restart docker
```

**Deliverables:**
- ✅ Jetson running in Super mode (67 TOPS)
- ✅ Docker with NVIDIA runtime working
- ✅ Dockerfile for reproducible environment

**Verification:**
```bash
docker run --rm --gpus all nvidia/cuda:11.4.0-base-ubuntu20.04 nvidia-smi
```

---

#### Task 1.2: oLLM Server Setup
**Estimated Time:** 3-5 hours

```bash
# 1. Install oLLM
pip install ollm

# 2. Download Phi-3-mini 4-bit quantized
# Model: microsoft/Phi-3-mini-4k-instruct-iq4_xs-GGUF
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf

# 3. Configure oLLM for SSD offloading
# Create config: offload weights + KV cache to NVMe SSD
ollm configure --model phi-3-mini-q4.gguf \
               --offload-kv-cache \
               --offload-weights \
               --max-context 4096
```

**Key Configuration:**
```python
# oLLM server configuration
OLLM_CONFIG = {
    "model_path": "/models/phi-3-mini-q4.gguf",
    "context_length": 4096,
    "offload_kv_cache": True,
    "offload_layers": 32,  # All layers to SSD
    "gpu_layers": 0,  # VRAM for inference only
    "threads": 4
}
```

**Deliverables:**
- ✅ oLLM server running on Jetson
- ✅ Phi-3 model loaded with SSD offloading
- ✅ Benchmark: tokens/sec and latency measured

**Verification:**
```python
# Test prompt
response = ollm.generate(
    "You are a Connect 4 player. Given board: [[0,0,0,0,0,0,0]...], select column:",
    max_tokens=50
)
# Expected: 2-5 seconds response time
```

---

#### Task 1.3: Python Environment & Repository
**Estimated Time:** 1-2 hours

```bash
# 1. Create project structure
mkdir -p prometheus_v0_75/{agents,game,tests,config}
cd prometheus_v0_75

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
cat > requirements.txt <<EOF
pygame>=2.5.0
numpy>=1.24.0
pydantic>=2.0.0
pytest>=7.4.0
ollm>=0.1.0
EOF

pip install -r requirements.txt

# 4. Initialize git
git init
git checkout -b v0.75
```

**Project Structure:**
```
prometheus_v0_75/
├── agents/
│   ├── strategy_agent.py
│   ├── move_generator.py
│   └── evaluator_agent.py
├── game/
│   ├── connect4.py
│   ├── board_renderer.py
│   └── game_state.py
├── communication/
│   ├── schemas.py
│   └── message_handler.py
├── config/
│   └── ollm_config.py
├── tests/
│   ├── test_agents.py
│   └── test_game.py
├── main.py
├── requirements.txt
└── Dockerfile
```

**Deliverables:**
- ✅ Clean project structure
- ✅ Git repository with v0.75 branch
- ✅ Virtual environment with dependencies

---

### Phase 2: Core Implementation (Week 2-3)

#### Task 2.1: Game Logic - Connect 4
**Estimated Time:** 4-6 hours

**File:** `game/connect4.py`

```python
"""
Connect 4 game logic
- 6x7 board
- Gravity-based piece placement
- Win condition: 4 in a row (horizontal, vertical, diagonal)
"""

import numpy as np
from typing import List, Tuple, Optional

class Connect4Game:
    def __init__(self):
        self.board = np.zeros((6, 7), dtype=int)
        self.current_player = 1  # 1 or -1
        self.move_history = []

    def get_legal_moves(self) -> List[int]:
        """Return list of columns that aren't full"""
        return [col for col in range(7) if self.board[0][col] == 0]

    def make_move(self, column: int) -> bool:
        """Drop piece in column, return True if valid"""
        if column not in self.get_legal_moves():
            return False

        # Find lowest empty row
        for row in range(5, -1, -1):
            if self.board[row][column] == 0:
                self.board[row][column] = self.current_player
                self.move_history.append((row, column))
                self.current_player *= -1  # Switch player
                return True
        return False

    def check_winner(self) -> Optional[int]:
        """Check for winner, return 1, -1, or None"""
        # Check horizontal
        for row in range(6):
            for col in range(4):
                if self._check_line(row, col, 0, 1):
                    return self.board[row][col]

        # Check vertical
        for row in range(3):
            for col in range(7):
                if self._check_line(row, col, 1, 0):
                    return self.board[row][col]

        # Check diagonals (both directions)
        for row in range(3):
            for col in range(4):
                if self._check_line(row, col, 1, 1):
                    return self.board[row][col]
                if self._check_line(row, col + 3, 1, -1):
                    return self.board[row][col + 3]

        return None

    def _check_line(self, row: int, col: int, dr: int, dc: int) -> bool:
        """Check if 4 in a row starting at (row, col) in direction (dr, dc)"""
        val = self.board[row][col]
        if val == 0:
            return False
        for i in range(1, 4):
            if self.board[row + i*dr][col + i*dc] != val:
                return False
        return True

    def is_full(self) -> bool:
        """Check if board is completely full"""
        return len(self.get_legal_moves()) == 0

    def get_state_dict(self) -> dict:
        """Return serializable game state"""
        return {
            "board": self.board.tolist(),
            "current_player": int(self.current_player),
            "legal_moves": self.get_legal_moves(),
            "move_count": len(self.move_history)
        }
```

**Deliverables:**
- ✅ Complete Connect 4 game engine
- ✅ Move validation
- ✅ Win detection
- ✅ Game state serialization

**Tests:**
```python
def test_initial_board():
    game = Connect4Game()
    assert game.get_legal_moves() == [0,1,2,3,4,5,6]
    assert game.check_winner() is None

def test_make_move():
    game = Connect4Game()
    assert game.make_move(3) == True
    assert game.board[5][3] == 1

def test_win_detection_horizontal():
    game = Connect4Game()
    for col in [0, 1, 2, 3]:
        game.make_move(col)  # Player 1
        if col < 3:
            game.make_move(col)  # Player -1
    assert game.check_winner() == 1
```

---

#### Task 2.2: pygame Visualization
**Estimated Time:** 3-4 hours

**File:** `game/board_renderer.py`

```python
"""
Real-time Connect 4 board visualization using pygame
"""

import pygame
import numpy as np

class BoardRenderer:
    def __init__(self, width=700, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Prometheus v0.75 - Connect 4")

        # Colors
        self.BLUE = (0, 100, 200)
        self.BLACK = (0, 0, 0)
        self.RED = (255, 0, 0)
        self.YELLOW = (255, 255, 0)

        # Board dimensions
        self.ROWS = 6
        self.COLS = 7
        self.SQUARE_SIZE = 100
        self.RADIUS = int(self.SQUARE_SIZE / 2 - 5)

    def draw_board(self, board: np.ndarray):
        """Draw the current board state"""
        # Draw blue board with black holes
        for row in range(self.ROWS):
            for col in range(self.COLS):
                pygame.draw.rect(
                    self.screen,
                    self.BLUE,
                    (col * self.SQUARE_SIZE,
                     row * self.SQUARE_SIZE + self.SQUARE_SIZE,
                     self.SQUARE_SIZE,
                     self.SQUARE_SIZE)
                )
                pygame.draw.circle(
                    self.screen,
                    self.BLACK,
                    (int(col * self.SQUARE_SIZE + self.SQUARE_SIZE / 2),
                     int(row * self.SQUARE_SIZE + self.SQUARE_SIZE + self.SQUARE_SIZE / 2)),
                    self.RADIUS
                )

        # Draw pieces
        for row in range(self.ROWS):
            for col in range(self.COLS):
                if board[row][col] == 1:
                    color = self.RED
                elif board[row][col] == -1:
                    color = self.YELLOW
                else:
                    continue

                pygame.draw.circle(
                    self.screen,
                    color,
                    (int(col * self.SQUARE_SIZE + self.SQUARE_SIZE / 2),
                     int(row * self.SQUARE_SIZE + self.SQUARE_SIZE + self.SQUARE_SIZE / 2)),
                    self.RADIUS
                )

        pygame.display.update()

    def handle_events(self) -> Optional[int]:
        """Handle user input, return column if clicked"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return -1  # Signal to quit

            if event.type == pygame.MOUSEBUTTONDOWN:
                posx = event.pos[0]
                col = int(posx // self.SQUARE_SIZE)
                return col

        return None

    def display_message(self, message: str):
        """Display text message on screen"""
        font = pygame.font.SysFont("monospace", 48)
        label = font.render(message, True, (255, 255, 255))
        self.screen.blit(label, (40, 10))
        pygame.display.update()

    def close(self):
        """Clean up pygame"""
        pygame.quit()
```

**Deliverables:**
- ✅ Real-time board rendering
- ✅ Visual piece placement
- ✅ Mouse input handling (for human player)
- ✅ Status message display

---

#### Task 2.3: Communication Schemas
**Estimated Time:** 2-3 hours

**File:** `communication/schemas.py`

```python
"""
JSON schemas for inter-agent communication
Enforces structured, validated messages
"""

from pydantic import BaseModel, Field
from typing import List, Literal

class MoveRequest(BaseModel):
    """Request from StrategyAgent to MoveGeneratorAgent"""
    message_type: Literal["move_request"] = "move_request"
    board_state: List[List[int]] = Field(description="6x7 board as 2D list")
    current_player: int = Field(description="1 or -1")
    legal_moves: List[int] = Field(description="Valid column indices")

class MoveResponse(BaseModel):
    """Response from MoveGeneratorAgent"""
    message_type: Literal["move_response"] = "move_response"
    column: int = Field(ge=0, le=6, description="Selected column 0-6")
    reasoning: str = Field(default="", description="LLM's explanation")

class MoveValidation(BaseModel):
    """Validation result from EvaluatorAgent"""
    message_type: Literal["move_validation"] = "move_validation"
    is_valid: bool
    column: int
    error_message: str = ""

class GameState(BaseModel):
    """Complete game state snapshot"""
    board: List[List[int]]
    current_player: int
    move_count: int
    legal_moves: List[int]
    winner: int | None = None
    is_complete: bool = False
```

**Deliverables:**
- ✅ Pydantic models for all message types
- ✅ Automatic validation
- ✅ Type safety
- ✅ JSON serialization/deserialization

---

#### Task 2.4: Agent Implementation
**Estimated Time:** 6-8 hours

**File:** `agents/strategy_agent.py`
```python
"""
StrategyAgent - Task dispatcher (simplified for v0.75)
"""

from communication.schemas import MoveRequest

class StrategyAgent:
    def __init__(self):
        self.name = "StrategyAgent"

    def create_move_request(self, game_state: dict) -> MoveRequest:
        """Create standardized move request"""
        return MoveRequest(
            board_state=game_state["board"],
            current_player=game_state["current_player"],
            legal_moves=game_state["legal_moves"]
        )
```

**File:** `agents/move_generator.py`
```python
"""
MoveGeneratorAgent - Interfaces with local LLM
"""

import json
from typing import Dict
from communication.schemas import MoveRequest, MoveResponse

class MoveGeneratorAgent:
    def __init__(self, ollm_client):
        self.ollm = ollm_client
        self.name = "MoveGeneratorAgent"

    def generate_move(self, request: MoveRequest) -> MoveResponse:
        """Generate move using LLM with retry logic"""
        prompt = self._format_prompt(request)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                raw_response = self.ollm.generate(prompt, max_tokens=100)
                response = self._parse_response(raw_response, request.legal_moves)
                return response
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < max_retries - 1:
                    # Retry with error context
                    prompt += f"\n\nPrevious attempt failed: {e}. Please respond with valid JSON."
                    continue
                else:
                    # Fallback to random legal move
                    import random
                    return MoveResponse(
                        column=random.choice(request.legal_moves),
                        reasoning="Fallback: LLM response parsing failed"
                    )

    def _format_prompt(self, request: MoveRequest) -> str:
        """Format board state into LLM prompt"""
        board_str = "\n".join([
            " ".join(["R" if cell == 1 else "Y" if cell == -1 else "." for cell in row])
            for row in request.board_state
        ])

        prompt = f"""You are an expert Connect 4 player.

Board (R=Red/You, Y=Yellow/Opponent, .=Empty):
{board_str}

Columns: 0 1 2 3 4 5 6

Your color: {'Red' if request.current_player == 1 else 'Yellow'}
Legal moves: {request.legal_moves}

Select a column to drop your piece. Respond ONLY with JSON:
{{"column": <0-6>, "reasoning": "<brief explanation>"}}

Your response:"""
        return prompt

    def _parse_response(self, raw_text: str, legal_moves: List[int]) -> MoveResponse:
        """Parse LLM response into MoveResponse"""
        # Extract JSON from response
        json_start = raw_text.find("{")
        json_end = raw_text.rfind("}") + 1
        json_str = raw_text[json_start:json_end]

        data = json.loads(json_str)

        # Validate column is legal
        column = int(data["column"])
        if column not in legal_moves:
            raise ValueError(f"Column {column} not in legal moves {legal_moves}")

        return MoveResponse(
            column=column,
            reasoning=data.get("reasoning", "")
        )
```

**File:** `agents/evaluator_agent.py`
```python
"""
EvaluatorAgent - Rules engine for move validation
"""

from communication.schemas import MoveResponse, MoveValidation
from game.connect4 import Connect4Game

class EvaluatorAgent:
    def __init__(self):
        self.name = "EvaluatorAgent"

    def validate_move(self, move: MoveResponse, game: Connect4Game) -> MoveValidation:
        """Validate if move is legal"""
        legal_moves = game.get_legal_moves()

        if move.column not in legal_moves:
            return MoveValidation(
                is_valid=False,
                column=move.column,
                error_message=f"Column {move.column} is not a legal move. Legal: {legal_moves}"
            )

        return MoveValidation(
            is_valid=True,
            column=move.column
        )
```

**Deliverables:**
- ✅ StrategyAgent (task dispatcher)
- ✅ MoveGeneratorAgent (LLM interface with retry logic)
- ✅ EvaluatorAgent (move validator)
- ✅ JSON parsing with error handling

---

#### Task 2.5: Main Orchestrator
**Estimated Time:** 3-4 hours

**File:** `main.py`

```python
"""
Main orchestrator for Prometheus v0.75
Manages game loop and agent coordination
"""

import sys
from game.connect4 import Connect4Game
from game.board_renderer import BoardRenderer
from agents.strategy_agent import StrategyAgent
from agents.move_generator import MoveGeneratorAgent
from agents.evaluator_agent import EvaluatorAgent
from config.ollm_config import get_ollm_client

def main():
    # Initialize components
    print("Initializing Prometheus v0.75...")
    ollm_client = get_ollm_client()
    game = Connect4Game()
    renderer = BoardRenderer()

    # Initialize agents
    strategy = StrategyAgent()
    move_gen = MoveGeneratorAgent(ollm_client)
    evaluator = EvaluatorAgent()

    print("✓ All systems ready")
    print("✓ Starting Connect 4 game...")
    print("  Red (AI) vs Yellow (Human)")

    running = True
    while running:
        # Render current board
        renderer.draw_board(game.board)

        # Check for game over
        winner = game.check_winner()
        if winner is not None:
            msg = "Red Wins!" if winner == 1 else "Yellow Wins!"
            renderer.display_message(msg)
            pygame.time.wait(3000)
            break

        if game.is_full():
            renderer.display_message("Draw!")
            pygame.time.wait(3000)
            break

        # Determine whose turn
        if game.current_player == 1:
            # AI's turn (Red)
            renderer.display_message("AI thinking...")
            print(f"\n--- AI's Turn (Red) ---")

            # Step 1: Strategy creates request
            request = strategy.create_move_request(game.get_state_dict())
            print(f"Legal moves: {request.legal_moves}")

            # Step 2: MoveGenerator produces move
            move = move_gen.generate_move(request)
            print(f"AI selected column: {move.column}")
            print(f"Reasoning: {move.reasoning}")

            # Step 3: Evaluator validates
            validation = evaluator.validate_move(move, game)

            if validation.is_valid:
                game.make_move(move.column)
                print("✓ Move executed")
            else:
                print(f"✗ Invalid move: {validation.error_message}")
                print("Retrying...")
                continue

        else:
            # Human's turn (Yellow)
            renderer.display_message("Your turn (Yellow)")
            print(f"\n--- Your Turn (Yellow) ---")
            print(f"Legal moves: {game.get_legal_moves()}")

            column = renderer.handle_events()

            if column == -1:
                # Quit signal
                running = False
                break

            if column is not None:
                if game.make_move(column):
                    print(f"✓ Human played column {column}")
                else:
                    print(f"✗ Illegal move")

    renderer.close()
    print("\nGame ended. Thanks for playing!")

if __name__ == "__main__":
    main()
```

**Deliverables:**
- ✅ Complete game loop
- ✅ Agent coordination
- ✅ Turn-based play (AI vs Human)
- ✅ Real-time visualization updates

---

### Phase 3: Testing & Verification (Week 3)

#### Task 3.1: Unit Tests
**Estimated Time:** 4-6 hours

**File:** `tests/test_agents.py`

```python
"""
Unit tests for agent components
"""

import pytest
from agents.strategy_agent import StrategyAgent
from agents.evaluator_agent import EvaluatorAgent
from game.connect4 import Connect4Game
from communication.schemas import MoveRequest, MoveResponse

def test_strategy_agent_creates_valid_request():
    strategy = StrategyAgent()
    game = Connect4Game()
    request = strategy.create_move_request(game.get_state_dict())

    assert isinstance(request, MoveRequest)
    assert len(request.board_state) == 6
    assert len(request.board_state[0]) == 7
    assert request.legal_moves == [0,1,2,3,4,5,6]

def test_evaluator_accepts_legal_move():
    evaluator = EvaluatorAgent()
    game = Connect4Game()
    move = MoveResponse(column=3, reasoning="Center column")

    validation = evaluator.validate_move(move, game)
    assert validation.is_valid == True

def test_evaluator_rejects_illegal_move():
    evaluator = EvaluatorAgent()
    game = Connect4Game()

    # Fill column 3
    for _ in range(6):
        game.make_move(3)

    move = MoveResponse(column=3, reasoning="Full column")
    validation = evaluator.validate_move(move, game)
    assert validation.is_valid == False
```

**File:** `tests/test_game.py`
```python
"""
Tests for game logic
"""

import pytest
from game.connect4 import Connect4Game

def test_initial_state():
    game = Connect4Game()
    assert game.current_player == 1
    assert len(game.get_legal_moves()) == 7
    assert game.check_winner() is None

def test_move_execution():
    game = Connect4Game()
    result = game.make_move(3)
    assert result == True
    assert game.board[5][3] == 1
    assert game.current_player == -1

def test_horizontal_win():
    game = Connect4Game()
    # Player 1 wins horizontally
    for col in [0, 1, 2, 3]:
        game.make_move(col)
        if col < 3:
            game.make_move(col)  # Player 2 fills same columns
    assert game.check_winner() == 1

def test_vertical_win():
    game = Connect4Game()
    # Player 1 wins vertically in column 0
    for _ in range(4):
        game.make_move(0)  # Player 1
        game.make_move(1)  # Player 2
    assert game.check_winner() == 1
```

**Run tests:**
```bash
pytest tests/ -v
```

**Deliverables:**
- ✅ Comprehensive unit test suite
- ✅ >80% code coverage
- ✅ All tests passing

---

#### Task 3.2: Integration Test
**Estimated Time:** 2-3 hours

```bash
# Create integration test script
cat > test_integration.sh <<'EOF'
#!/bin/bash

echo "=== Prometheus v0.75 Integration Test ==="

echo "1. Testing oLLM server connection..."
python -c "
from config.ollm_config import get_ollm_client
client = get_ollm_client()
response = client.generate('Test prompt', max_tokens=10)
print(f'✓ oLLM server responding')
"

echo "2. Testing game engine..."
python -c "
from game.connect4 import Connect4Game
game = Connect4Game()
game.make_move(3)
assert game.board[5][3] == 1
print('✓ Game engine working')
"

echo "3. Testing agent chain..."
python -c "
from agents.strategy_agent import StrategyAgent
from agents.evaluator_agent import EvaluatorAgent
from game.connect4 import Connect4Game

game = Connect4Game()
strategy = StrategyAgent()
evaluator = EvaluatorAgent()

request = strategy.create_move_request(game.get_state_dict())
print(f'✓ Agent chain working')
"

echo "4. Testing full orchestration (automated 5 moves)..."
python -c "
from main import run_automated_test
run_automated_test(num_moves=5)
print('✓ Full orchestration working')
"

echo ""
echo "=== All Integration Tests Passed ==="
EOF

chmod +x test_integration.sh
./test_integration.sh
```

**Deliverables:**
- ✅ End-to-end integration test
- ✅ Automated test suite
- ✅ Performance benchmarks recorded

---

### Phase 4: Documentation & Delivery (Week 4)

#### Task 4.1: Docker Container
**Estimated Time:** 2-3 hours

**File:** `Dockerfile`

```dockerfile
# Dockerfile for Prometheus v0.75
FROM nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Download model (if not mounted)
RUN mkdir -p /models && \
    wget -O /models/phi-3-mini-q4.gguf \
    https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf || true

# Configure oLLM
RUN python3 -c "from config.ollm_config import setup_ollm; setup_ollm()"

# Run tests on build (optional)
# RUN pytest tests/ -v

EXPOSE 8000

CMD ["python3", "main.py"]
```

**Build & Run:**
```bash
# Build image
docker build -t prometheus-v0.75:latest .

# Run with GPU support
docker run --rm --gpus all \
  -v /dev/shm:/dev/shm \
  -p 8000:8000 \
  prometheus-v0.75:latest
```

**Deliverables:**
- ✅ Complete Dockerfile
- ✅ Reproducible environment
- ✅ GPU support configured

---

#### Task 4.2: Documentation
**Estimated Time:** 3-4 hours

**File:** `README_V0_75.md`

```markdown
# Prometheus v0.75: Foundational Refactor for Gaming & Edge AI

## Overview

Prometheus v0.75 demonstrates the Causal Agentic Mesh (CAM) architecture
running entirely on NVIDIA Jetson Orin Nano edge hardware, playing
Connect 4 using a locally-served 4-bit quantized Phi-3 model.

## Quick Start

### Prerequisites
- NVIDIA Jetson Orin Nano 8GB Developer Kit
- JetPack SDK 5.1+
- 20GB free SSD space
- Display (HDMI) + Mouse

### Installation
```bash
git clone <repo> && cd prometheus_v0_75
./setup_jetson.sh
source venv/bin/activate
python main.py
```

## Architecture

### Agents
- **StrategyAgent**: Task dispatcher
- **MoveGeneratorAgent**: LLM interface (Phi-3)
- **EvaluatorAgent**: Move validator

### Communication
- JSON schema-validated messages
- Pydantic models for type safety
- Automatic retry on malformed responses

### Hardware Optimization
- oLLM with SSD offloading (weights + KV cache)
- 4-bit quantized model (~2.3GB)
- Inference: 2-5 seconds per move
- VRAM usage: <2GB

## Performance Benchmarks

| Metric | Value |
|--------|-------|
| Tokens/sec | 8-15 |
| Move latency | 2-5 sec |
| VRAM usage | 1.8 GB |
| RAM usage | 3.2 GB |

## Testing

```bash
# Unit tests
pytest tests/ -v

# Integration test
./test_integration.sh

# Manual play
python main.py
```

## Troubleshooting

### oLLM server not responding
```bash
# Check server status
ollm status

# Restart server
ollm restart
```

### Slow inference
```bash
# Verify Super mode enabled
sudo nvpmodel -q

# Should show: NV Power Mode: MAXN
```

## Next Steps

v0.80 will add:
- CRLS learning loop
- Performance graphing
- Win rate improvement over time
```

**Deliverables:**
- ✅ Comprehensive README
- ✅ Setup guide
- ✅ Troubleshooting section
- ✅ Architecture diagrams

---

## 📊 Success Metrics

### Must Have (v0.75)
- [ ] Play complete Connect 4 game without crashes
- [ ] Real-time pygame visualization updates
- [ ] All moves are legal
- [ ] Inference runs entirely on Jetson (no cloud)
- [ ] Response time: <10 seconds per move

### Nice to Have
- [ ] Automated opponent (random/minimax)
- [ ] Game replay/history
- [ ] Performance logging
- [ ] Docker deployment

### Future (v0.80+)
- Learning loop (CRLS)
- Win rate improvement
- Performance graphs
- Chess support

---

## 📝 Documentation Deliverables

1. ✅ **This roadmap** - Implementation guide
2. **README_V0_75.md** - User documentation
3. **ARCHITECTURE_V0_75.md** - Technical architecture
4. **JETSON_SETUP_GUIDE.md** - Hardware setup
5. **API_REFERENCE.md** - Agent APIs
6. **TESTING_GUIDE.md** - Test procedures

---

## ⏱️ Timeline Summary

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1: Setup** | Week 1 (20-30 hrs) | Jetson, oLLM, Python env |
| **Phase 2: Core** | Week 2-3 (40-50 hrs) | Game, agents, orchestrator |
| **Phase 3: Testing** | Week 3 (10-15 hrs) | Unit, integration tests |
| **Phase 4: Docs** | Week 4 (10-15 hrs) | Docker, documentation |
| **Total** | **3-4 weeks** | **80-110 hours** |

---

## 🚀 Getting Started

### Immediate Next Steps

1. **Verify Jetson availability**
   ```bash
   ls /home/pmc/jetson* || echo "Jetson files not found"
   ```

2. **Create project structure**
   ```bash
   mkdir prometheus_v0_75
   cd prometheus_v0_75
   git init
   git checkout -b v0.75
   ```

3. **Begin with Task 1.1: Jetson Hardware Configuration**

---

## 📚 Resources

### Documentation
- [oLLM GitHub](https://github.com/vllm-project/vllm)
- [Phi-3 Model Card](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct)
- [Jetson Orin Nano Datasheet](https://developer.nvidia.com/embedded/jetson-orin-nano)
- [pygame Documentation](https://www.pygame.org/docs/)

### References from Workplan
- Connect 4 rules and strategy
- pygame tutorials
- JSON schema validation
- Pydantic models

---

**Status:** 🟢 Ready to begin implementation
**Next Action:** Start Phase 1, Task 1.1 (Jetson setup)
