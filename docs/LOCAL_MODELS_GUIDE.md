# Local Model Guide for IOI Bronze

## Overview

IOI Bronze v0.75 now supports **local foundation models** for code generation, eliminating the need for cloud APIs. This is especially useful for:

- **Privacy**: All data stays on your machine
- **Cost**: No API fees
- **Speed**: No network latency (once loaded)
- **Offline**: Works without internet

## Recommended Models for Jetson Orin Nano (4GB GPU)

### 1. **DeepSeek-Coder-1.3B** ⭐ (RECOMMENDED)
- **Size**: ~800MB (4-bit quantized)
- **Quality**: Excellent for competitive programming
- **Speed**: ~2-3 tokens/sec on Jetson
- **Memory**: ~1.5GB GPU when loaded
- **Download**:
  ```bash
  wget https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf
  ```

### 2. **Phi-3-mini (3.8B)**
- **Size**: ~2.3GB (4-bit quantized)
- **Quality**: Strong reasoning, good code generation
- **Speed**: ~1-2 tokens/sec on Jetson
- **Memory**: ~2.5GB GPU
- **Download**:
  ```bash
  wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
  ```

### 3. **CodeLlama-7B** (Advanced)
- **Size**: ~3.5GB (4-bit quantized)
- **Quality**: Meta's specialized code model
- **Speed**: ~0.5-1 tokens/sec on Jetson
- **Memory**: ~3.8GB GPU (tight on 4GB!)
- **Download**:
  ```bash
  wget https://huggingface.co/TheBloke/CodeLlama-7B-GGUF/resolve/main/codellama-7b.Q4_K_M.gguf
  ```

## Quick Installation

### Option 1: Automated Script (Easiest)

```bash
# Run the installation script
chmod +x install_local_models.sh
./install_local_models.sh
```

This will:
1. Build llama.cpp with CUDA support
2. Download DeepSeek-Coder-1.3B
3. Set up environment variables
4. Test the model

### Option 2: Manual Installation

#### Step 1: Install llama.cpp

```bash
# Clone and build
cd ~
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

mkdir -p build
cd build
cmake .. -DGGML_CUDA=ON  # Enable GPU support
cmake --build . --config Release -j4

# Install binary
sudo cp bin/llama-cli /usr/local/bin/
```

#### Step 2: Download a model

```bash
# Create models directory
mkdir -p ~/ioi_models
cd ~/ioi_models

# Download DeepSeek-Coder-1.3B (recommended)
wget https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf
```

#### Step 3: Set environment variable

```bash
# For current session
export IOI_LOCAL_MODEL="$HOME/ioi_models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf"

# Add to .bashrc for permanent
echo 'export IOI_LOCAL_MODEL="$HOME/ioi_models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf"' >> ~/.bashrc
```

## Usage in Python

### Basic Usage

```python
from prometheus_ioi_bronze import PrometheusIOIBronze
import os

# Initialize with local model
system = PrometheusIOIBronze(
    local_model_path=os.environ['IOI_LOCAL_MODEL'],
    use_local=True,
    population_size=20,
    max_generations=10
)

# Solve a problem
problem = {
    'text': "Count how many even numbers are in the array",
    'examples': [
        {'input': '5\n2 4 6 8 10', 'output': '5'},
        {'input': '3\n1 3 5', 'output': '0'}
    ]
}

result = system.solve_problem(
    problem['text'],
    problem['examples'],
    verbose=True
)

if result['solved']:
    print(f"✅ Solved! Code:\n{result['code']}")
```

### Direct Synthesizer Usage

```python
from ioi_synthesizer_local import IOICodeSynthesizer
import os

# Initialize synthesizer
synthesizer = IOICodeSynthesizer(
    local_model_path=os.environ['IOI_LOCAL_MODEL'],
    use_local=True
)

# Generate code
code = synthesizer.synthesize(
    problem_text="Count even numbers in array",
    examples=[{'input': '5\n2 4 6 8 10', 'output': '5'}],
    algorithm_sequence=['use_array', 'count_if']
)

print(code)
```

### Fallback Modes

The system automatically falls back in this order:

1. **Local model** (if `IOI_LOCAL_MODEL` is set and llama.cpp available)
2. **Cloud model** (if `GOOGLE_API_KEY` is set)
3. **Mock mode** (template-based generation)

```python
# Automatic fallback
system = PrometheusIOIBronze()  # Will use best available option
```

## Performance Comparison

| Model | Size | Speed (tokens/sec) | Quality | Memory (GPU) |
|-------|------|-------------------|---------|--------------|
| **DeepSeek-Coder-1.3B** | 800MB | 2-3 | ⭐⭐⭐⭐ | 1.5GB |
| **Phi-3-mini** | 2.3GB | 1-2 | ⭐⭐⭐⭐ | 2.5GB |
| **CodeLlama-7B** | 3.5GB | 0.5-1 | ⭐⭐⭐⭐⭐ | 3.8GB |
| **Gemini (cloud)** | N/A | 5-10 | ⭐⭐⭐⭐⭐ | 0 (cloud) |

**Recommendation**: Start with DeepSeek-Coder-1.3B for best balance of speed, quality, and memory on Jetson.

## Testing the Installation

```bash
# Test llama.cpp directly
llama-cli \
    -m ~/ioi_models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf \
    -p "Write a Python function to count even numbers in a list" \
    --temp 0.3 \
    -n 256 \
    -ngl 35 \
    -c 2048

# Test Python integration
python3 ioi_synthesizer_local.py

# Test full IOI Bronze system
python3 prometheus_ioi_bronze.py
```

## Troubleshooting

### "llama-cli not found"

```bash
# Check if llama.cpp is built
ls ~/llama.cpp/build/bin/llama-cli

# Add to PATH if needed
export PATH="$HOME/llama.cpp/build/bin:$PATH"
echo 'export PATH="$HOME/llama.cpp/build/bin:$PATH"' >> ~/.bashrc
```

### "CUDA not available" or slow inference

```bash
# Verify CUDA is working
nvidia-smi

# Rebuild llama.cpp with CUDA
cd ~/llama.cpp/build
cmake .. -DGGML_CUDA=ON
cmake --build . --config Release -j4
```

### Out of memory errors

1. **Try smaller model**: Use DeepSeek-1.3B instead of CodeLlama-7B
2. **Reduce GPU layers**: Edit `ioi_synthesizer_local.py`, change `n_gpu_layers=35` to `n_gpu_layers=20`
3. **Use CPU only**: Set `n_gpu_layers=0` (slower but uses less GPU memory)

### Model download interrupted

```bash
# Resume download with wget -c
cd ~/ioi_models
wget -c https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf
```

## Advanced: Using Different Models

To switch models, just update the environment variable:

```bash
# Use Phi-3-mini instead
export IOI_LOCAL_MODEL="$HOME/ioi_models/Phi-3-mini-4k-instruct-q4.gguf"

# Or CodeLlama-7B
export IOI_LOCAL_MODEL="$HOME/ioi_models/codellama-7b.Q4_K_M.gguf"
```

## Architecture Details

The local model integration uses:

- **llama.cpp**: Fast C++ inference engine with CUDA support
- **GGUF format**: Efficient quantized model format (4-bit, 5-bit, 8-bit)
- **Subprocess interface**: Python calls llama-cli binary
- **Same API**: LocalModelInference class mimics Gemini API

Key parameters:
- `-ngl 35`: Offload 35 layers to GPU (adjust based on memory)
- `-c 2048`: Context window size
- `--temp 0.3`: Low temperature for deterministic code generation
- `-n 2048`: Max output tokens

## Next Steps

1. **Install a local model** using the automated script or manual steps
2. **Test with sample problems** to verify it's working
3. **Benchmark on USACO Bronze** to compare local vs cloud quality
4. **Optimize parameters** (n_gpu_layers, temperature, etc.) based on your needs

## References

- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [DeepSeek-Coder models](https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF)
- [Phi-3 models](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
- [CodeLlama models](https://huggingface.co/TheBloke/CodeLlama-7B-GGUF)
- [GGUF format documentation](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)

---

*Generated for Prometheus IOI Bronze v0.75*
*Optimized for NVIDIA Jetson Orin Nano (4GB GPU)*
