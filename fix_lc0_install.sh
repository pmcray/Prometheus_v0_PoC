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

# The CMakeLists.txt is NOT in the root, it's in a subdirectory
# Let's check where it actually is
echo "Looking for CMakeLists.txt..."
find . -name "CMakeLists.txt" -type f | head -5

# Try building from the repository root
echo "Creating build directory..."
mkdir -p build
cd build

# Configure - let CMake find the right directory
echo "Configuring CMake..."
# For lc0, we may need to use meson instead of cmake
cd ..

# Check if meson build system is used
if [ -f "meson.build" ]; then
    echo "Using Meson build system (lc0's actual build system)..."

    # Install meson and ninja if needed
    pip3 install meson ninja || echo "Meson/ninja already installed"

    # Build with meson
    ./build.sh

    # Copy binary
    if [ -f "build/release/lc0" ]; then
        sudo cp build/release/lc0 /usr/local/bin/
        sudo chmod +x /usr/local/bin/lc0
        echo "✅ Leela Chess Zero installed via Meson!"
    else
        echo "❌ Build failed - binary not found"
        exit 1
    fi
else
    echo "Trying CMake approach..."
    cd build
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
fi

echo "✅ Leela Chess Zero installed!"
echo ""
echo "Testing installation..."
lc0 --version

echo ""
echo "✅ Installation complete!"
echo ""
echo "Note: GPU support may not work without proper CUDA backend."
echo "For CPU-only mode, lc0 will use BLAS backend."
