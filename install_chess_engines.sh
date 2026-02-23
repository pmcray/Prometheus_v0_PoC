#!/bin/bash
# Install Chess Engines for Prometheus
# Stockfish (CPU) and Leela Chess Zero (GPU)

set -e  # Exit on error

echo "🎮 Installing Chess Engines for Prometheus"
echo "==========================================="
echo ""

# Check if running on Jetson
if [ -f /etc/nv_tegra_release ]; then
    echo "✅ Detected NVIDIA Jetson platform"
    IS_JETSON=true
else
    echo "ℹ️  Running on standard Linux"
    IS_JETSON=false
fi

# 1. Install Stockfish (CPU baseline)
echo ""
echo "📦 Installing Stockfish (CPU)..."
echo "--------------------------------"

if command -v stockfish &> /dev/null; then
    echo "✅ Stockfish already installed: $(stockfish --version 2>&1 | head -1)"
else
    echo "Installing Stockfish via apt..."
    sudo apt-get update
    sudo apt-get install -y stockfish

    if command -v stockfish &> /dev/null; then
        echo "✅ Stockfish installed: $(stockfish --version 2>&1 | head -1)"
    else
        echo "⚠️  Stockfish installation failed, trying manual install..."

        # Manual install
        cd /tmp
        wget https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-ubuntu-x86-64-avx2.tar
        tar -xvf stockfish-ubuntu-x86-64-avx2.tar
        sudo cp stockfish/stockfish-ubuntu-x86-64-avx2 /usr/local/bin/stockfish
        sudo chmod +x /usr/local/bin/stockfish

        echo "✅ Stockfish installed manually"
    fi
fi

# 2. Install Leela Chess Zero (GPU)
echo ""
echo "🎮 Installing Leela Chess Zero (GPU)..."
echo "----------------------------------------"

if command -v lc0 &> /dev/null; then
    echo "✅ Leela already installed: $(lc0 --version 2>&1 | head -1)"
else
    echo "Building Leela Chess Zero from source..."

    # Install dependencies
    sudo apt-get install -y cmake g++ git libboost-all-dev zlib1g-dev

    # Install CUDA toolkit if not present
    if ! command -v nvcc &> /dev/null; then
        echo "Installing CUDA toolkit..."
        if [ "$IS_JETSON" = true ]; then
            sudo apt-get install -y nvidia-cuda-toolkit
        else
            sudo apt-get install -y nvidia-cuda-toolkit
        fi
    fi

    # Clone and build Leela
    cd /tmp
    if [ -d "lc0" ]; then
        rm -rf lc0
    fi

    git clone --recursive https://github.com/LeelaChessZero/lc0.git
    cd lc0

    mkdir -p build && cd build

    # Configure for CUDA
    if [ "$IS_JETSON" = true ]; then
        # Jetson-specific configuration
        cmake .. \
            -DCUDA=ON \
            -DCUDNN=ON \
            -DCMAKE_CUDA_ARCHITECTURES=87 \
            -DCMAKE_BUILD_TYPE=Release
    else
        # Standard x86_64 configuration
        cmake .. \
            -DCUDA=ON \
            -DCUDNN=ON \
            -DCMAKE_BUILD_TYPE=Release
    fi

    # Build (use fewer cores on Jetson to avoid OOM)
    if [ "$IS_JETSON" = true ]; then
        make -j2
    else
        make -j$(nproc)
    fi

    # Install
    sudo cp lc0 /usr/local/bin/
    sudo chmod +x /usr/local/bin/lc0

    echo "✅ Leela Chess Zero installed"
fi

# 3. Download Leela neural network weights
echo ""
echo "📥 Downloading Leela Neural Networks..."
echo "---------------------------------------"

mkdir -p ~/.lc0/networks
cd ~/.lc0/networks

# Download T60 network (smaller, faster)
if [ ! -f "t60.pb.gz" ]; then
    echo "Downloading T60 network (faster inference)..."
    wget -O t60.pb.gz "https://training.lczero.org/get_network?sha=00af53b0b5942a911a26e5f05f5ca0e3f36d60f0c9f078b0f1e08e3c8558a4c6"
    echo "✅ T60 network downloaded"
else
    echo "✅ T60 network already exists"
fi

# Download T80 network (stronger, slower)
if [ ! -f "t80.pb.gz" ]; then
    echo "Downloading T80 network (stronger play)..."
    wget -O t80.pb.gz "https://training.lczero.org/get_network?sha=0c1a20e5c35eb319e68280d7d6c80d857e5f5c0e656e5a85f0e8e3c8558a4c7"
    echo "✅ T80 network downloaded"
else
    echo "✅ T80 network already exists"
fi

# 4. Test installations
echo ""
echo "🧪 Testing Installations..."
echo "---------------------------"

echo ""
echo "Testing Stockfish..."
if stockfish --version &> /dev/null; then
    echo "✅ Stockfish working: $(which stockfish)"
else
    echo "❌ Stockfish test failed"
fi

echo ""
echo "Testing Leela Chess Zero..."
if lc0 --version &> /dev/null; then
    echo "✅ Leela working: $(which lc0)"

    # Test GPU backend
    echo ""
    echo "Testing GPU backend..."
    timeout 5 lc0 --weights=~/.lc0/networks/t60.pb.gz --backend=cuda-auto 2>&1 | grep -i "cuda\|gpu" || echo "⚠️  GPU detection unclear, check manually"
else
    echo "❌ Leela test failed"
fi

# 5. Summary
echo ""
echo "✅ Installation Complete!"
echo "========================"
echo ""
echo "Installed Engines:"
echo "  - Stockfish: $(which stockfish 2>/dev/null || echo 'Not found')"
echo "  - Leela (lc0): $(which lc0 2>/dev/null || echo 'Not found')"
echo ""
echo "Neural Networks:"
echo "  - T60 (fast): ~/.lc0/networks/t60.pb.gz"
echo "  - T80 (strong): ~/.lc0/networks/t80.pb.gz"
echo ""
echo "Next Steps:"
echo "  1. Test with Stockfish:"
echo "     python prometheus_chess_uci_gpu.py --engine stockfish --games 10"
echo ""
echo "  2. Test with Leela (GPU):"
echo "     python prometheus_chess_uci_gpu.py --engine lc0 --weights ~/.lc0/networks/t60.pb.gz --gpu --games 10"
echo ""
echo "  3. Start live dashboard:"
echo "     streamlit run prometheus_live_dashboard.py"
echo ""
echo "  4. Long-run training (24 hours):"
echo "     python prometheus_chess_uci_gpu.py --engine lc0 --weights ~/.lc0/networks/t80.pb.gz --gpu --games 2000 --hours 24"
echo ""
