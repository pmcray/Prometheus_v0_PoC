# GPU-Accelerated Game Engine Setup Guide

**For Jetson Orin Nano and Linux Systems**
**Date:** October 9, 2025

---

## Overview

This guide covers installation of GPU-accelerated game engines for the Prometheus benchmarking roadmap.

---

## 1. Leela Chess Zero (LCZero) - GPU Chess

### Installation on Jetson Orin Nano

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y cmake g++ git libboost-all-dev zlib1g-dev

# Install CUDA toolkit (if not already installed)
sudo apt-get install -y nvidia-cuda-toolkit

# Clone Leela Chess Zero
git clone --recursive https://github.com/LeelaChessZero/lc0.git
cd lc0

# Build with CUDA backend
mkdir build && cd build
cmake .. -DCUDA=ON -DCUDNN=ON
make -j4

# Binary will be at: build/lc0
sudo cp lc0 /usr/local/bin/
```

### Download Neural Network Weights

```bash
# Create weights directory
mkdir -p ~/.lc0/networks

# Download a strong network (T80 - 80 blocks, ~600MB)
cd ~/.lc0/networks
wget https://training.lczero.org/get_network?sha=00af53b0b5942a911a26e5f05f5ca0e3f36d60f0c9f078b0f1e08e3c8558a4c6 -O t80.pb.gz

# Or smaller network for faster inference (T60)
wget https://training.lczero.org/get_network?sha=0c1a20e5c35eb319e68280d7d6c80d857e5f5c0e656e5a85 -O t60.pb.gz
```

### Test Installation

```bash
# Run Leela with GPU
lc0 --weights=~/.lc0/networks/t80.pb.gz --backend=cuda

# Should see output like:
# "CUDA GPU detected: Orin"
# "Using CUDA backend"
```

### Usage in Prometheus

```python
from prometheus_chess_uci_gpu import PrometheusChessUCI

agent = PrometheusChessUCI(
    opponent_engine_path="/usr/local/bin/lc0",
    use_gpu=True,
    leela_weights="~/.lc0/networks/t80.pb.gz",
    starting_elo=800.0
)

agent.train(num_games=1000, checkpoint_interval=50)
```

---

## 2. KataGo - GPU Go Engine

### Installation on Jetson Orin Nano

```bash
# Download pre-built binary for ARM64
cd /tmp
wget https://github.com/lightvector/KataGo/releases/download/v1.14.1/katago-v1.14.1-cuda11.8-linux-arm64.zip

unzip katago-v1.14.1-cuda11.8-linux-arm64.zip
sudo cp katago /usr/local/bin/
sudo chmod +x /usr/local/bin/katago

# Or build from source for latest version
git clone https://github.com/lightvector/KataGo.git
cd KataGo/cpp
cmake . -DUSE_BACKEND=CUDA
make -j4
sudo cp katago /usr/local/bin/
```

### Download Neural Network

```bash
# Create KataGo directory
mkdir -p ~/.katago/networks

cd ~/.katago/networks

# Download strong 40-block network (~400MB)
wget https://github.com/lightvector/KataGo/releases/download/v1.14.1/kata1-b40c256-s11840935168-d2898845681.bin.gz

# Extract
gunzip kata1-b40c256-s11840935168-d2898845681.bin.gz

# Download default config
cd ~/.katago
wget https://raw.githubusercontent.com/lightvector/KataGo/master/cpp/configs/gtp_example.cfg
```

### Test Installation

```bash
# Run KataGo in GTP mode
katago gtp -model ~/.katago/networks/kata1-b40c256-s11840935168-d2898845681.bin \
           -config ~/.katago/gtp_example.cfg

# Should see:
# "CUDA backend detected"
# "Using GPU 0: Orin"
```

---

## 3. Stockfish (CPU Baseline)

### Installation

```bash
# Install from package manager
sudo apt-get install -y stockfish

# Or download latest version
wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-ubuntu-x86-64-avx2.tar
tar -xvf stockfish-ubuntu-x86-64-avx2.tar
sudo cp stockfish/stockfish-ubuntu-x86-64-avx2 /usr/local/bin/stockfish
```

### Usage

```python
agent = PrometheusChessUCI(
    opponent_engine_path="/usr/bin/stockfish",
    use_gpu=False,  # Stockfish is CPU-only
    starting_elo=800.0
)
```

---

## 4. Performance Comparison

| Engine | Hardware | Speed (nodes/sec) | Strength (Elo) | GPU Required |
|--------|----------|------------------|----------------|--------------|
| Stockfish 16 | CPU (4 cores) | ~2M | 3500+ | ❌ |
| LCZero T80 | Jetson Orin (GPU) | ~5K | 3200+ | ✅ |
| LCZero T60 | Jetson Orin (GPU) | ~10K | 3000+ | ✅ |
| KataGo b40 | Jetson Orin (GPU) | ~50K | 3800+ (Go) | ✅ |

---

## 5. Training Duration Benefits

### Chess (Leela or Stockfish)

| Duration | Expected Elo | Capabilities Gained |
|----------|-------------|-------------------|
| 1 hour | 1000-1200 | Basic tactics, simple openings |
| 4 hours | 1400-1600 | Positional play, developed opening book |
| 12 hours | 1700-1900 | Advanced strategy, endgame technique |
| 24+ hours | 1900-2100 | Expert-level, refined repertoire |

### Go (KataGo)

| Duration | Expected Rank | Capabilities |
|----------|--------------|-------------|
| 1 hour | 15-10 kyu | Basic patterns, simple joseki |
| 4 hours | 10-5 kyu | Territory evaluation, life/death |
| 12 hours | 5 kyu - 1 dan | Strategic planning, fuseki knowledge |
| 24+ hours | 1-3 dan | High-level understanding |

---

## 6. Long-Run Training Commands

### Chess - 24 Hour Training

```bash
# With Leela (GPU)
python prometheus_chess_uci_gpu.py \
    --engine /usr/local/bin/lc0 \
    --weights ~/.lc0/networks/t80.pb.gz \
    --gpu \
    --games 2000 \
    --hours 24 \
    --start-elo 800

# With Stockfish (CPU)
python prometheus_chess_uci_gpu.py \
    --engine /usr/bin/stockfish \
    --games 2000 \
    --hours 24 \
    --start-elo 800
```

### Go - 24 Hour Training

```bash
python prometheus_go_gtp.py \
    --engine /usr/local/bin/katago \
    --model ~/.katago/networks/kata1-b40c256-s11840935168-d2898845681.bin \
    --config ~/.katago/gtp_example.cfg \
    --games 1000 \
    --hours 24 \
    --board-size 19
```

---

## 7. Monitoring GPU Usage

```bash
# Watch GPU utilization during training
watch -n 1 nvidia-smi

# Should see:
# - GPU Utilization: 90-100%
# - Memory Usage: 4-6 GB (Leela), 6-8 GB (KataGo)
# - Temperature: 50-70°C
```

---

## 8. Troubleshooting

### Leela: "CUDA backend not available"

```bash
# Check CUDA installation
nvcc --version

# Rebuild with CUDA
cd lc0/build
cmake .. -DCUDA=ON -DCUDNN=ON -DCMAKE_CUDA_ARCHITECTURES=87
make clean && make -j4
```

### KataGo: "No GPU detected"

```bash
# Check that CUDA libraries are found
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Run with verbose logging
katago gtp -model <model> -config <config> -log-file katago.log
cat katago.log | grep -i cuda
```

### Out of Memory Errors

```bash
# For Leela: Use smaller network
# T60 instead of T80 (uses ~40% less memory)

# For KataGo: Reduce batch size in config
# Edit gtp_example.cfg:
# numSearchThreads = 4  (reduce from default 8)
```

---

## 9. Recommended Setup for Jetson Orin Nano

```bash
# Install all engines
./install_stockfish.sh
./install_lc0.sh
./install_katago.sh

# Download all networks
./download_networks.sh

# Verify installations
python verify_engines.py

# Start 24-hour multi-domain training
./run_tier1_longrun.sh
```

---

## 10. Cloud Alternative (Google Colab)

If Jetson GPU is insufficient, use Google Colab with T4/A100:

```python
# In Colab notebook:
!apt-get install -y stockfish
!pip install chess

# Clone Prometheus
!git clone https://github.com/pmcray/Prometheus_v0_PoC.git
%cd Prometheus_v0_PoC

# Run training with Colab GPU
!python prometheus_chess_uci_gpu.py --engine stockfish --games 5000 --hours 12
```

Colab advantages:
- Free T4 GPU (faster than Jetson)
- No local setup required
- Easy to share notebooks

Disadvantages:
- 12-hour runtime limit (use checkpointing)
- Intermittent disconnections

---

**Next Steps:**
1. Install engines following this guide
2. Run short test (10 games) to verify setup
3. Start long-run training (24+ hours)
4. Monitor results in `chess_uci_results/` directory

🤖 Generated with [Claude Code](https://claude.com/claude-code)
