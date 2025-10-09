#!/bin/bash
# Fix Leela Chess Zero installation
# Run this after install_chess_engines.sh fails

set -e

echo "🔧 Fixing Leela Chess Zero Installation"
echo "========================================"

cd /tmp

# Clean up any existing build
if [ -d "lc0" ]; then
    echo "Removing old lc0 directory..."
    rm -rf lc0
fi

# Clone fresh
echo "Cloning Leela Chess Zero..."
git clone --recursive https://github.com/LeelaChessZero/lc0.git
cd lc0

# Build from the root directory (it has CMakeLists.txt there)
echo "Creating build directory..."
mkdir -p build
cd build

# Configure with CUDA
echo "Configuring CMake with CUDA support..."
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -Dgtest=OFF

# Build
echo "Building lc0 (this will take 10-15 minutes)..."
make -j2

# Install
echo "Installing lc0..."
sudo cp lc0 /usr/local/bin/
sudo chmod +x /usr/local/bin/lc0

echo "✅ Leela Chess Zero installed!"
echo ""
echo "Testing installation..."
lc0 --version

echo ""
echo "✅ Installation complete!"
echo ""
echo "Note: GPU support may not work without proper CUDA backend."
echo "For CPU-only mode, lc0 will use BLAS backend."
