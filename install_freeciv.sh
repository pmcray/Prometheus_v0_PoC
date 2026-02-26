#!/bin/bash
# Install FreeCiv for PrometheusStar

echo "======================================================================"
echo "Installing FreeCiv Server for PrometheusStar"
echo "======================================================================"
echo ""

# Install FreeCiv server (headless - no GUI needed)
echo "Installing freeciv-server package..."
SUDO=""
if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
fi

$SUDO apt-get update
$SUDO apt-get install -y freeciv-server freeciv-data

# Verify installation
if command -v freeciv-server &> /dev/null; then
    echo ""
    echo "======================================================================"
    echo "✅ FreeCiv installed successfully!"
    echo "======================================================================"
    freeciv-server --version
    echo ""
    echo "FreeCiv server is ready for AI training!"
else
    echo ""
    echo "❌ Installation failed"
    echo "Please install manually: sudo apt-get install freeciv-server"
fi
