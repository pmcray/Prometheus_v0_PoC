# Prometheus AI - Troubleshooting Guide

Complete troubleshooting guide for common issues with Prometheus AI.

**Last Updated**: 2025-11-28

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Training Problems](#training-problems)
3. [Runtime Errors](#runtime-errors)
4. [Docker Issues](#docker-issues)
5. [GPU & CUDA Problems](#gpu--cuda-problems)
6. [Performance Issues](#performance-issues)
7. [Notebook Problems](#notebook-problems)
8. [Model Issues](#model-issues)
9. [Network & Deployment](#network--deployment)
10. [General Debugging](#general-debugging)

---

## Installation Issues

### Problem: `pip install` fails with permission errors

**Symptoms**:
```
ERROR: Could not install packages due to an PermissionError
```

**Solutions**:

1. **Use virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Install for user only**:
```bash
pip install --user -r requirements.txt
```

3. **Use sudo** (not recommended):
```bash
sudo pip install -r requirements.txt
```

---

### Problem: `ModuleNotFoundError: No module named 'tensorflow'`

**Symptoms**:
```python
>>> import tensorflow
ModuleNotFoundError: No module named 'tensorflow'
```

**Solutions**:

1. **Install TensorFlow**:
```bash
pip install tensorflow>=2.15.0
```

2. **Verify Python environment**:
```bash
which python  # Should point to venv if using virtual env
pip list | grep tensorflow
```

3. **Reinstall dependencies**:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Problem: `ERROR: Failed building wheel for chess`

**Symptoms**:
```
ERROR: Failed building wheel for chess
ERROR: Could not build wheels for chess
```

**Solutions**:

1. **Install python-chess separately**:
```bash
pip install python-chess
```

2. **Install build tools**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev build-essential

# macOS
xcode-select --install

# Windows
# Install Visual Studio Build Tools
```

3. **Try pre-built wheel**:
```bash
pip install --only-binary :all: python-chess
```

---

### Problem: Python version incompatibility

**Symptoms**:
```
ERROR: Package requires Python 3.10 or higher
```

**Solutions**:

1. **Check Python version**:
```bash
python --version
python3 --version
```

2. **Install Python 3.10+**:
```bash
# Ubuntu/Debian
sudo apt-get install python3.10

# macOS (using Homebrew)
brew install python@3.10

# Windows
# Download from https://www.python.org/downloads/
```

3. **Create venv with specific Python**:
```bash
python3.10 -m venv venv
source venv/bin/activate
```

---

## Training Problems

### Problem: Training is extremely slow

**Symptoms**:
- Training taking 10+ hours per model
- CPU usage at 100%
- No GPU utilization

**Solutions**:

1. **Use GPU** (3-10x faster):
```bash
# Install TensorFlow with GPU support
pip install tensorflow[and-cuda]>=2.15.0

# Verify GPU detection
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

2. **Reduce training games**:
```bash
# Quick training (15-30 min)
python scripts/train_pretrained_models.py --model go_9x9 --games 50

# Disable MCTS during training
python scripts/train_pretrained_models.py --model go_9x9 --no-mcts
```

3. **Optimize TensorFlow settings**:
```python
import tensorflow as tf

# Enable mixed precision (2x faster on modern GPUs)
tf.keras.mixed_precision.set_global_policy('mixed_float16')

# Enable XLA compilation
tf.config.optimizer.set_jit(True)
```

---

### Problem: Out of Memory (OOM) during training

**Symptoms**:
```
ResourceExhaustedError: OOM when allocating tensor
```

**Solutions**:

1. **Enable GPU memory growth**:
```python
import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
```

2. **Reduce batch size** in training script:
```python
# In scripts/train_pretrained_models.py
# Change: batch_size=64 -> batch_size=32
```

3. **Train smaller models first**:
```bash
# Train 9x9 before 19x19
python scripts/train_pretrained_models.py --model go_9x9
# Then train 19x19 via transfer learning
python scripts/train_pretrained_models.py --model go_19x19
```

4. **Close other applications**:
```bash
# Check memory usage
free -h  # Linux
# Close browser, IDEs, etc.
```

5. **Reduce MCTS simulations**:
```python
# In training script
# Change: num_simulations=400 -> num_simulations=200
```

---

### Problem: Training crashes or freezes

**Symptoms**:
- Training stops without error
- Process hangs indefinitely
- System becomes unresponsive

**Solutions**:

1. **Monitor system resources**:
```bash
# Linux
htop  # CPU/RAM
nvidia-smi -l 1  # GPU

# Check for OOM killer
dmesg | grep -i "out of memory"
```

2. **Add checkpointing**:
```python
# Save progress periodically
if game_num % 50 == 0:
    model.save(f'checkpoint_{game_num}.h5')
```

3. **Reduce resource usage**:
- Train one model at a time
- Don't run multiple notebooks simultaneously
- Close unnecessary applications

4. **Check disk space**:
```bash
df -h
# Ensure at least 5GB free
```

---

### Problem: Poor model performance after training

**Symptoms**:
- Win rate <60% vs random
- ELO <1000
- Model plays poorly

**Causes & Solutions**:

1. **Too few training games**:
```bash
# Train with more games
python scripts/train_pretrained_models.py --model go_9x9 --games 500
```

2. **MCTS disabled during training**:
```bash
# Enable MCTS (default, but verify)
python scripts/train_pretrained_models.py --model go_9x9 --mcts
# Check that --no-mcts is NOT used
```

3. **Training interrupted**:
```bash
# Delete corrupted model and retrain
rm models/pretrained/go_9x9.h5
python scripts/train_pretrained_models.py --model go_9x9
```

4. **Learning rate too high/low**:
```python
# Adjust in training script
optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)  # Try 0.0001 or 0.01
```

---

## Runtime Errors

### Problem: `ImportError: cannot import name 'X' from 'prometheus'`

**Symptoms**:
```python
ImportError: cannot import name 'add_mcts' from 'prometheus.mcts'
```

**Solutions**:

1. **Reinstall package**:
```bash
pip install -e .
```

2. **Check file exists**:
```bash
ls -la prometheus/mcts.py
# or
ls -la prometheus/mcts/__init__.py
```

3. **Verify module structure**:
```python
import prometheus
print(prometheus.__file__)
# Should point to your local directory
```

4. **Clear Python cache**:
```bash
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
```

---

### Problem: `AttributeError: module has no attribute`

**Symptoms**:
```python
AttributeError: module 'prometheus.models' has no attribute 'PrometheusGoAgent'
```

**Solutions**:

1. **Import correctly**:
```python
# Wrong
from prometheus.models import PrometheusGoAgent

# Correct
from prometheus.models.go_models import PrometheusGoAgent
```

2. **Check imports in __init__.py**:
```bash
cat prometheus/models/__init__.py
# Should export the class
```

3. **Reload module**:
```python
import importlib
import prometheus.models.go_models
importlib.reload(prometheus.models.go_models)
```

---

### Problem: `ValueError: Invalid board state` or game errors

**Symptoms**:
```
ValueError: Invalid board state
ValueError: Move is not legal
```

**Solutions**:

1. **Check input format**:
```python
# Go: moves are (row, col) tuples
move = (3, 3)  # Correct
# move = [3, 3]  # May cause issues

# Chess: moves are UCI strings
move = "e2e4"  # Correct
```

2. **Validate legal moves**:
```python
legal_moves = env.get_legal_actions()
if move in legal_moves:
    env.step(move)
```

3. **Reset environment**:
```python
env.reset()
# Start fresh
```

---

## Docker Issues

### Problem: `docker: command not found`

**Symptoms**:
```bash
$ docker --version
bash: docker: command not found
```

**Solutions**:

1. **Install Docker**:
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# macOS
# Download Docker Desktop from https://www.docker.com/products/docker-desktop

# Windows
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
```

2. **Add user to docker group** (Linux):
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

3. **Verify installation**:
```bash
docker --version
docker run hello-world
```

---

### Problem: `permission denied while trying to connect to Docker daemon`

**Symptoms**:
```
permission denied while trying to connect to the Docker daemon socket
```

**Solutions**:

1. **Add user to docker group**:
```bash
sudo usermod -aG docker $USER
newgrp docker  # Or log out and back in
```

2. **Use sudo** (temporary fix):
```bash
sudo docker-compose up -d
```

3. **Check Docker socket permissions**:
```bash
ls -la /var/run/docker.sock
sudo chmod 666 /var/run/docker.sock  # Not recommended for production
```

---

### Problem: `docker-compose: command not found`

**Symptoms**:
```bash
$ docker-compose --version
bash: docker-compose: command not found
```

**Solutions**:

1. **Install docker-compose**:
```bash
# Docker Desktop (includes compose)
# Or install separately:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Use `docker compose` (Docker v2)**:
```bash
docker compose up -d
# Note: no hyphen
```

---

### Problem: Docker build fails

**Symptoms**:
```
ERROR [internal] load metadata for docker.io/library/python:3.10-slim
```

**Solutions**:

1. **Check internet connection**:
```bash
ping -c 3 docker.io
```

2. **Clear Docker cache**:
```bash
docker system prune -a
```

3. **Specify base image tag**:
```dockerfile
# In Dockerfile.production
FROM python:3.10-slim-bullseye
```

4. **Check disk space**:
```bash
df -h
docker system df
```

---

## GPU & CUDA Problems

### Problem: GPU not detected

**Symptoms**:
```python
>>> tf.config.list_physical_devices('GPU')
[]
```

**Solutions**:

1. **Install NVIDIA drivers**:
```bash
# Check current drivers
nvidia-smi

# Install (Ubuntu)
sudo apt-get install nvidia-driver-535
sudo reboot
```

2. **Install CUDA Toolkit**:
```bash
# TensorFlow 2.15 requires CUDA 11.8+
# Download from: https://developer.nvidia.com/cuda-downloads
```

3. **Install cuDNN**:
```bash
# Download from: https://developer.nvidia.com/cudnn
# TensorFlow 2.15 requires cuDNN 8.6+
```

4. **Reinstall TensorFlow GPU**:
```bash
pip uninstall tensorflow
pip install tensorflow[and-cuda]>=2.15.0
```

5. **Verify CUDA installation**:
```bash
nvcc --version
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

---

### Problem: CUDA out of memory

**Symptoms**:
```
tensorflow.python.framework.errors_impl.ResourceExhaustedError: OOM when allocating tensor
```

**Solutions**:

1. **Enable memory growth**:
```python
import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)
```

2. **Set memory limit**:
```python
import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    tf.config.set_logical_device_configuration(
        gpus[0],
        [tf.config.LogicalDeviceConfiguration(memory_limit=4096)]  # 4GB
    )
```

3. **Reduce batch size**:
```python
# In training/inference code
batch_size = 16  # Down from 32 or 64
```

4. **Clear GPU memory**:
```python
import tensorflow as tf
from tensorflow.keras import backend as K

K.clear_session()
tf.compat.v1.reset_default_graph()
```

---

### Problem: CUDA version mismatch

**Symptoms**:
```
Could not load dynamic library 'libcudart.so.11.0'
```

**Solutions**:

1. **Check CUDA version compatibility**:
```bash
nvcc --version
```

TensorFlow 2.15 requires:
- CUDA 11.8 or 12.x
- cuDNN 8.6+

2. **Update CUDA**:
```bash
# Uninstall old CUDA
sudo apt-get --purge remove "*cuda*" "*cublas*" "*cufft*" "*cufile*" "*curand*" "*cusolver*" "*cusparse*" "*gds-tools*" "*npp*" "*nvjpeg*" "nsight*" "*nvvm*"

# Install compatible CUDA
# Download from: https://developer.nvidia.com/cuda-downloads
```

3. **Use TensorFlow compatible with your CUDA**:
```bash
# For CUDA 11.2
pip install tensorflow==2.10.0

# For CUDA 11.8 / 12.x
pip install tensorflow>=2.15.0
```

---

## Performance Issues

### Problem: Inference is very slow

**Symptoms**:
- Taking >100ms per inference
- MCTS taking minutes per move
- Games timing out

**Solutions**:

1. **Use GPU**:
```python
import tensorflow as tf
print(tf.config.list_physical_devices('GPU'))
# Should show GPU
```

2. **Enable XLA compilation**:
```python
import tensorflow as tf
tf.config.optimizer.set_jit(True)
```

3. **Reduce MCTS simulations**:
```python
agent = add_mcts(base_agent, num_simulations=200)  # Down from 400
```

4. **Use model quantization**:
```python
# Convert to TFLite with quantization
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()
```

5. **Batch predictions**:
```python
# Instead of one at a time
predictions = model.predict(batch_of_states)
```

---

### Problem: High memory usage

**Symptoms**:
- System RAM fills up
- Swap usage high
- System becomes sluggish

**Solutions**:

1. **Clear sessions**:
```python
from tensorflow.keras import backend as K
K.clear_session()
```

2. **Delete old models**:
```python
import gc
del model
gc.collect()
```

3. **Reduce cached data**:
```python
# Limit MCTS tree size
mcts_agent = add_mcts(agent, num_simulations=200, max_tree_size=10000)
```

4. **Monitor memory**:
```bash
# Linux
watch -n 1 free -h

# GPU memory
nvidia-smi -l 1
```

---

## Notebook Problems

### Problem: Notebook kernel crashes in Colab

**Symptoms**:
- "Your session crashed for an unknown reason"
- Kernel restarts unexpectedly

**Solutions**:

1. **Reduce resource usage**:
```python
# Set QUICK_DEMO mode
QUICK_DEMO = True

# Reduce games/epochs
num_games = 10  # Instead of 100
```

2. **Use GPU runtime**:
- Runtime → Change runtime type → GPU

3. **Clear outputs before running**:
- Edit → Clear all outputs
- Then run cells

4. **Restart runtime**:
- Runtime → Restart runtime
- Run all cells again

---

### Problem: Notebooks can't import prometheus

**Symptoms**:
```
ModuleNotFoundError: No module named 'prometheus'
```

**Solutions**:

1. **In Colab**: Run installation cell:
```python
!pip install git+https://github.com/pmcray/Prometheus_v0_PoC.git
```

2. **Locally**: Install package:
```bash
pip install -e .
```

3. **Add to sys.path** (temporary):
```python
import sys
sys.path.append('/path/to/Prometheus_v0_PoC')
```

---

### Problem: Plots don't display in notebook

**Symptoms**:
- No output from matplotlib plots
- Blank cells where plots should be

**Solutions**:

1. **Enable inline plots**:
```python
%matplotlib inline
import matplotlib.pyplot as plt
```

2. **Show plots explicitly**:
```python
plt.plot([1, 2, 3])
plt.show()  # Add this
```

3. **Restart kernel**:
- Kernel → Restart & Clear Output

---

## Model Issues

### Problem: Model file not found

**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'models/pretrained/go_9x9.h5'
```

**Solutions**:

1. **Create directory**:
```bash
mkdir -p models/pretrained
```

2. **Train the model**:
```bash
python scripts/train_pretrained_models.py --model go_9x9
```

3. **Download pre-trained model**:
```bash
python scripts/download_models.py --model go_9x9
```

4. **Check current directory**:
```bash
pwd  # Should be in Prometheus_v0_PoC
ls models/pretrained/
```

---

### Problem: Model fails to load

**Symptoms**:
```
ValueError: Unable to load model
OSError: Unable to open file (file signature not found)
```

**Solutions**:

1. **Check file integrity**:
```bash
file models/pretrained/go_9x9.h5
# Should say: models/pretrained/go_9x9.h5: Hierarchical Data Format (version 5) data
```

2. **Redownload model**:
```bash
rm models/pretrained/go_9x9.h5
python scripts/download_models.py --model go_9x9
```

3. **Retrain model**:
```bash
rm models/pretrained/go_9x9.h5
python scripts/train_pretrained_models.py --model go_9x9
```

4. **Use custom loader**:
```python
import tensorflow as tf
model = tf.keras.models.load_model('models/pretrained/go_9x9.h5', compile=False)
model.compile(optimizer='adam', loss='mse')
```

---

## Network & Deployment

### Problem: Bot fails to connect to Lichess/OGS

**Symptoms**:
```
ConnectionError: Failed to connect to api.lichess.org
401 Unauthorized
```

**Solutions**:

1. **Check API token**:
```bash
# Verify token in .env
cat .env | grep LICHESS_BOT_TOKEN

# Token should start with lip_
```

2. **Regenerate token**:
- Lichess: https://lichess.org/account/oauth/token
- OGS: https://online-go.com/developer

3. **Check network**:
```bash
ping api.lichess.org
curl https://lichess.org
```

4. **Verify bot account**:
- Lichess: Account must be upgraded to BOT account
- Can't use regular player account for bots

---

### Problem: Docker bot restarts constantly

**Symptoms**:
```bash
$ docker-compose ps
go-bot     restarting
```

**Solutions**:

1. **Check logs**:
```bash
docker-compose logs go-bot
```

2. **Common issues**:
- Missing API token in `.env`
- Model file not found
- Invalid configuration

3. **Fix .env**:
```bash
cp .env.example .env
nano .env
# Add valid tokens
```

4. **Rebuild**:
```bash
docker-compose down
docker-compose up -d --build
```

---

## General Debugging

### Enable verbose logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# TensorFlow logging
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'  # All messages
```

### Check environment

```bash
python scripts/verify_phase_b_readiness.py
```

### Get system info

```python
import sys
import tensorflow as tf
import numpy as np

print(f"Python: {sys.version}")
print(f"TensorFlow: {tf.__version__}")
print(f"NumPy: {np.__version__}")
print(f"GPU: {tf.config.list_physical_devices('GPU')}")
```

### Reset everything

```bash
# Delete venv
rm -rf venv/

# Create fresh venv
python3 -m venv venv
source venv/bin/activate

# Reinstall
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# Verify
python -c "import prometheus; print('OK')"
```

---

## Still Having Issues?

1. **Check FAQ**: [FAQ.md](FAQ.md)
2. **Verification checklist**: [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)
3. **GitHub Issues**: https://github.com/pmcray/Prometheus_v0_PoC/issues

When reporting issues, include:
- Error messages (full stack trace)
- Python version (`python --version`)
- OS (Linux/macOS/Windows)
- GPU info (`nvidia-smi` output if applicable)
- Steps to reproduce

---

**Last Updated**: 2025-11-28
