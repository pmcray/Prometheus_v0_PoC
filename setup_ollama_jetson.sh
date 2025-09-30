#!/bin/bash
# Setup Ollama on Jetson Orin Nano for Prometheus v0.69
# This script installs Ollama and downloads recommended models

set -e  # Exit on error

echo "================================================"
echo "🚀 Prometheus v0.69 - Ollama Setup for Jetson"
echo "================================================"
echo ""

# Check if running on Jetson
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠️  Warning: Not running on Jetson hardware"
else
    echo "✓ Detected: $(cat /proc/device-tree/model)"
fi

echo ""
echo "📦 Step 1: Installing Ollama..."
echo "--------------------"

# Install Ollama
if command -v ollama &> /dev/null; then
    echo "✓ Ollama already installed: $(ollama --version)"
else
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama installed"
fi

# Install Python client
echo ""
echo "📦 Step 2: Installing Python dependencies..."
echo "--------------------"
pip install -q ollama || echo "⚠️  Failed to install ollama package"
echo "✓ Python ollama client installed"

# Start Ollama service
echo ""
echo "🔧 Step 3: Starting Ollama service..."
echo "--------------------"
sudo systemctl enable ollama 2>/dev/null || echo "Note: systemd service not available, will run manually"
sudo systemctl start ollama 2>/dev/null || {
    echo "Starting Ollama in background..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
}
echo "✓ Ollama service started"

# Pull recommended models
echo ""
echo "📥 Step 4: Downloading recommended models..."
echo "================================================"

# Model 1: Primary code generation (6.7B model, ~4GB)
echo ""
echo "Downloading deepseek-coder:6.7b-instruct-q4_K_M (Primary - Code Generation)"
echo "  Size: ~4GB | Use: Main coding tasks, refactoring"
echo "  Speed: Medium | Quality: Excellent"
echo "--------------------"
ollama pull deepseek-coder:6.7b-instruct-q4_K_M

# Model 2: Fast mutations (3B model, ~1.9GB)
echo ""
echo "Downloading qwen2.5-coder:3b-instruct-q4_K_M (Fast - Mutations/Crossover)"
echo "  Size: ~1.9GB | Use: Evolutionary operations"
echo "  Speed: Very Fast | Quality: Good"
echo "--------------------"
ollama pull qwen2.5-coder:3b-instruct-q4_K_M

# Model 3: Reasoning/Planning (7B model, ~4GB)
echo ""
echo "Downloading mistral:7b-instruct-q4_K_M (Reasoning - Planning)"
echo "  Size: ~4GB | Use: GeneralistPlanner, strategy"
echo "  Speed: Medium | Quality: Excellent"
echo "--------------------"
ollama pull mistral:7b-instruct-q4_K_M

echo ""
echo "================================================"
echo "✅ Ollama Setup Complete!"
echo "================================================"
echo ""
echo "Installed Models:"
ollama list
echo ""
echo "GPU Status:"
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader 2>/dev/null || echo "GPU info not available"
echo ""
echo "🎯 Next Steps:"
echo "  1. Test Ollama: ollama run deepseek-coder:6.7b-instruct-q4_K_M 'print hello world in python'"
echo "  2. Run Prometheus: python -m prometheus.smm"
echo "  3. Open demo: jupyter notebook Prometheus_v0_69_demo.ipynb"
echo ""
echo "📝 Model Selection Guide:"
echo "  - Code generation:  deepseek-coder:6.7b"
echo "  - Fast evolution:   qwen2.5-coder:3b"
echo "  - Planning/Reason:  mistral:7b"
echo ""
echo "🔥 Ready for local GPU-accelerated AI!"
