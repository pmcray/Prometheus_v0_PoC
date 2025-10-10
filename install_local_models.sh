#!/bin/bash
# Install llama.cpp and download local models for IOI Bronze
# Optimized for NVIDIA Jetson Orin Nano (4GB GPU)

set -e

echo "=========================================="
echo "IOI Bronze - Local Model Installation"
echo "=========================================="

# Create models directory
MODEL_DIR="$HOME/ioi_models"
mkdir -p "$MODEL_DIR"

# Step 1: Install llama.cpp with CUDA support
echo ""
echo "📦 Step 1: Installing llama.cpp with CUDA support..."

if [ ! -d "$HOME/llama.cpp" ]; then
    cd "$HOME"
    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp

    # Build with CUDA
    mkdir -p build
    cd build
    cmake .. -DGGML_CUDA=ON
    cmake --build . --config Release -j4

    # Install binary
    sudo cp bin/llama-cli /usr/local/bin/ || cp bin/llama-cli "$HOME/.local/bin/"

    echo "✅ llama.cpp installed successfully"
else
    echo "✅ llama.cpp already installed"
fi

# Verify installation
if command -v llama-cli &> /dev/null; then
    echo "✅ llama-cli is available in PATH"
else
    echo "⚠️  Warning: llama-cli not in PATH. You may need to add $HOME/.local/bin to PATH"
    export PATH="$HOME/.local/bin:$PATH"
fi

# Step 2: Download recommended model
echo ""
echo "📥 Step 2: Downloading DeepSeek-Coder-1.3B (recommended for Jetson)..."
echo "   Size: ~800MB (4-bit quantized)"

MODEL_FILE="$MODEL_DIR/deepseek-coder-1.3b-instruct.Q4_K_M.gguf"

if [ ! -f "$MODEL_FILE" ]; then
    cd "$MODEL_DIR"
    wget -c "https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf"
    echo "✅ Model downloaded successfully"
else
    echo "✅ Model already exists: $MODEL_FILE"
fi

# Step 3: Set environment variable
echo ""
echo "🔧 Step 3: Setting up environment..."

# Add to .bashrc if not already there
if ! grep -q "IOI_LOCAL_MODEL" "$HOME/.bashrc"; then
    echo "" >> "$HOME/.bashrc"
    echo "# IOI Bronze local model" >> "$HOME/.bashrc"
    echo "export IOI_LOCAL_MODEL=\"$MODEL_FILE\"" >> "$HOME/.bashrc"
    echo "✅ Added IOI_LOCAL_MODEL to .bashrc"
else
    echo "✅ IOI_LOCAL_MODEL already in .bashrc"
fi

# Set for current session
export IOI_LOCAL_MODEL="$MODEL_FILE"

# Step 4: Test the model
echo ""
echo "🧪 Step 4: Testing model..."

TEST_PROMPT="Write a Python function to count even numbers in a list."

echo "Test prompt: $TEST_PROMPT"
echo ""

llama-cli \
    -m "$MODEL_FILE" \
    -p "$TEST_PROMPT" \
    --temp 0.3 \
    -n 256 \
    -ngl 35 \
    -c 2048 \
    --no-display-prompt

echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "Model location: $MODEL_FILE"
echo "Environment variable: IOI_LOCAL_MODEL=$MODEL_FILE"
echo ""
echo "To use in Python:"
echo "  from ioi_synthesizer_local import IOICodeSynthesizer"
echo "  synthesizer = IOICodeSynthesizer(local_model_path=os.environ['IOI_LOCAL_MODEL'], use_local=True)"
echo ""
echo "To activate for this session:"
echo "  export IOI_LOCAL_MODEL=\"$MODEL_FILE\""
echo ""
echo "For future sessions, it's already in ~/.bashrc"
echo ""
echo "=========================================="
echo "Optional: Download additional models"
echo "=========================================="
echo ""
echo "Phi-3-mini (3.8B, ~2GB):"
echo "  wget -P $MODEL_DIR https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
echo ""
echo "CodeLlama-7B (4-bit, ~3.5GB - may be tight on 4GB GPU):"
echo "  wget -P $MODEL_DIR https://huggingface.co/TheBloke/CodeLlama-7B-GGUF/resolve/main/codellama-7b.Q4_K_M.gguf"
echo ""
