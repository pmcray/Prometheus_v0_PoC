# Jetson Quickstart Guide - Prometheus v0.75

## 🚀 Quick Setup on Jetson Orin Nano

### 1. Pull Latest Code
```bash
cd ~/Prometheus_v0_PoC
git fetch origin
git checkout v0.19
git pull origin v0.19
```

### 2. Review Documentation
```bash
# Main implementation roadmap
cat ROADMAP_V0_75.md | less

# v0.68 status (why we're skipping to v0.75)
cat V0_68_COMPLETION_STATUS.md
```

### 3. Verify You're on Jetson
```bash
# Check Jetson info
cat /etc/nv_tegra_release

# Check GPU
nvidia-smi

# Should show: Jetson Orin Nano
```

### 4. Enable Max Performance
```bash
# Switch to maximum performance mode
sudo nvpmodel -m 2  # MAXN mode (67 TOPS)
sudo jetson_clocks   # Lock clocks to maximum

# Verify
sudo nvpmodel -q
# Should show: NV Power Mode: MAXN
```

### 5. Create Project Structure
```bash
# Create new v0.75 directory
cd ~
mkdir -p prometheus_v0_75
cd prometheus_v0_75

# Initialize git
git init
git checkout -b v0.75

# Create structure
mkdir -p {agents,game,communication,config,tests}
```

### 6. Setup Python Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Create requirements.txt
cat > requirements.txt <<EOF
pygame>=2.5.0
numpy>=1.24.0
pydantic>=2.0.0
pytest>=7.4.0
EOF

# Install
pip install -r requirements.txt
```

### 7. Install oLLM
```bash
# Install oLLM for local LLM serving
pip install ollm

# Verify installation
python -c "import ollm; print('oLLM installed successfully')"
```

### 8. Download Phi-3 Model
```bash
# Create models directory
mkdir -p ~/models

# Download 4-bit quantized Phi-3-mini
cd ~/models
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf

# Verify download
ls -lh Phi-3-mini-4k-instruct-q4.gguf
# Should be ~2.3GB
```

## 📋 Next Steps

Follow the detailed roadmap in `ROADMAP_V0_75.md`:

**Phase 1: Environment Setup (Week 1)**
- Task 1.1: Jetson Hardware Configuration ✅ (if you did steps above)
- Task 1.2: oLLM Server Setup (configure SSD offloading)
- Task 1.3: Python Environment & Repository ✅ (if you did steps above)

**Phase 2: Core Implementation (Weeks 2-3)**
- Task 2.1: Game Logic - Connect 4
- Task 2.2: pygame Visualization
- Task 2.3: Communication Schemas
- Task 2.4: Agent Implementation
- Task 2.5: Main Orchestrator

## 🔍 Verify Your Setup

Run this verification script:

```bash
cat > verify_setup.sh <<'VERIFY'
#!/bin/bash
echo "=== Jetson Setup Verification ==="
echo ""

echo "1. Jetson Info:"
cat /etc/nv_tegra_release 2>/dev/null || echo "  Not on Jetson?"

echo ""
echo "2. GPU Status:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

echo ""
echo "3. Performance Mode:"
sudo nvpmodel -q | grep "NV Power Mode"

echo ""
echo "4. Python Version:"
python3 --version

echo ""
echo "5. Pip Packages:"
pip list | grep -E "pygame|numpy|pydantic|pytest|ollm" || echo "  Install required packages"

echo ""
echo "6. Model Status:"
if [ -f ~/models/Phi-3-mini-4k-instruct-q4.gguf ]; then
    ls -lh ~/models/Phi-3-mini-4k-instruct-q4.gguf
else
    echo "  ⚠ Model not downloaded yet"
fi

echo ""
echo "=== Setup verification complete ==="
VERIFY

chmod +x verify_setup.sh
./verify_setup.sh
```

## 📚 Key Files Reference

| File | Description |
|------|-------------|
| `ROADMAP_V0_75.md` | Complete implementation guide (15,000+ words) |
| `V0_68_COMPLETION_STATUS.md` | Why we're skipping to v0.75 |
| `Documents/Prometheus PoC AGI Workplan Development v0.75-v0.89.pdf` | Original specification |

## 🐛 Troubleshooting

### Can't find nvidia-smi
```bash
# Add to PATH
export PATH=/usr/local/cuda/bin:$PATH
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
```

### oLLM installation fails
```bash
# Try with explicit CUDA version
pip install ollm --extra-index-url https://download.pytorch.org/whl/cu118
```

### Low disk space
```bash
# Check space
df -h

# Clean up if needed
sudo apt clean
docker system prune -a
```

## 💡 Tips

1. **Work in tmux/screen** - Long-running processes won't die if SSH disconnects
   ```bash
   sudo apt install tmux
   tmux new -s prometheus
   # Ctrl+B then D to detach
   ```

2. **Monitor GPU usage**
   ```bash
   watch -n 1 nvidia-smi
   ```

3. **Check temperature**
   ```bash
   cat /sys/devices/virtual/thermal/thermal_zone*/temp
   ```

4. **Backup your work**
   ```bash
   git add . && git commit -m "Progress checkpoint"
   git push origin v0.75
   ```

## 🎯 Success Criteria for v0.75

You're done when you can:
- ✅ Launch a pygame window showing a Connect 4 board
- ✅ AI makes legal moves (even if random)
- ✅ Human can click to play
- ✅ Game detects wins/draws
- ✅ All runs locally on Jetson (no cloud)
- ✅ Response time <10 seconds per move

Good luck! 🚀
