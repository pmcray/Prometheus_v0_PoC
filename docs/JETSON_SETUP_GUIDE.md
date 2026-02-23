# Jetson Orin Nano Setup Guide for Prometheus v0.69-v0.74

**Target Platform:** NVIDIA Jetson Orin Nano (8GB)
**Purpose:** GPU-accelerated development with local LLMs for v0.69-v0.74 implementation
**Current Status:** v0.65-v0.68 complete and pushed to GitHub

---

## Part 1: Clone Repository to Jetson

### On Your Jetson Orin Nano

```bash
# Navigate to your workspace
cd ~
mkdir -p workspace
cd workspace

# Clone the repository
git clone https://github.com/pmcray/Prometheus_v0_PoC.git
cd Prometheus_v0_PoC

# Check out the v0.19 branch
git checkout v0.19

# Verify you have the latest code
git log --oneline -5
# Should show: 905a7e4 Implement Prometheus v0.65-v0.68: Generalized Capability Acquisition
```

---

## Part 2: System Dependencies

### Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y

# Install essential build tools
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    python3-pip \
    python3-dev \
    libopenblas-dev \
    libhdf5-serial-dev \
    hdf5-tools \
    libhdf5-dev \
    zlib1g-dev \
    zip \
    libjpeg8-dev \
    liblapack-dev \
    libblas-dev \
    gfortran
```

### Install JetPack SDK (if not already installed)
```bash
# Check JetPack version
sudo apt-cache show nvidia-jetpack
```

---

## Part 3: Python Environment

### Create Virtual Environment
```bash
cd ~/workspace/Prometheus_v0_PoC

# Create venv
python3 -m venv venv_jetson

# Activate
source venv_jetson/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### Install PyTorch for Jetson
```bash
# PyTorch 2.0+ with CUDA support for Jetson
# Check available versions: https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048

# For JetPack 5.x (recommended):
pip install torch torchvision torchaudio

# Or if you need a specific wheel:
# wget https://nvidia.box.com/shared/static/[specific-wheel].whl
# pip install torch-*.whl
```

### Install Core Dependencies
```bash
# Prometheus base requirements
pip install -r requirements.txt

# Additional requirements for v0.65-v0.68
pip install numpy pandas pytest pydantic
```

---

## Part 4: LLM Backend Setup

### Option A: llama.cpp (Recommended - Most Efficient)

```bash
# Install llama-cpp-python with CUDA support
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --no-cache-dir

# Verify installation
python3 -c "from llama_cpp import Llama; print('✓ llama.cpp installed successfully')"
```

### Option B: Transformers + bitsandbytes

```bash
# Install Hugging Face transformers
pip install transformers accelerate bitsandbytes

# For 4-bit quantization support
pip install scipy
```

---

## Part 5: Download Models

### Create Models Directory
```bash
mkdir -p ~/workspace/models
cd ~/workspace/models
```

### Download Code Generation LLM (for v0.69-v0.72)

**Option 1: DeepSeek-Coder 6.7B (Recommended for code evolution)**
```bash
# Install huggingface-cli
pip install huggingface-hub[cli]

# Download GGUF quantized model (4-bit, ~4GB)
huggingface-cli download TheBloke/deepseek-coder-6.7B-instruct-GGUF \
    deepseek-coder-6.7b-instruct.Q4_K_M.gguf \
    --local-dir ./deepseek-coder \
    --local-dir-use-symlinks False
```

**Option 2: CodeLlama 7B**
```bash
huggingface-cli download TheBloke/CodeLlama-7B-Instruct-GGUF \
    codellama-7b-instruct.Q4_K_M.gguf \
    --local-dir ./codellama \
    --local-dir-use-symlinks False
```

### Download Math/Reasoning LLM (for v0.71, v0.74)

```bash
# Llama 3.1 8B Instruct (strong reasoning)
huggingface-cli download TheBloke/Meta-Llama-3.1-8B-Instruct-GGUF \
    meta-llama-3.1-8b-instruct.Q4_K_M.gguf \
    --local-dir ./llama-3.1-8b \
    --local-dir-use-symlinks False
```

### Download Stable Diffusion (for v0.70)

```bash
# SDXL-Turbo (fast, good quality)
huggingface-cli download stabilityai/sdxl-turbo \
    --local-dir ./sdxl-turbo \
    --local-dir-use-symlinks False

# Or Stable Diffusion v1.5 (lighter, faster on Jetson)
huggingface-cli download runwayml/stable-diffusion-v1-5 \
    --local-dir ./sd-v1-5 \
    --local-dir-use-symlinks False
```

---

## Part 6: Test Installation

### Test PyTorch CUDA
```bash
python3 << 'EOF'
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
EOF
```

Expected output:
```
PyTorch version: 2.x.x
CUDA available: True
CUDA version: 11.x
GPU: Orin
Memory: 8.00 GB
```

### Test llama.cpp
```bash
cd ~/workspace/Prometheus_v0_PoC

python3 << 'EOF'
from llama_cpp import Llama

# Load model
model_path = "~/workspace/models/deepseek-coder/deepseek-coder-6.7b-instruct.Q4_K_M.gguf"
llm = Llama(
    model_path=model_path,
    n_ctx=4096,
    n_gpu_layers=-1,  # Use all GPU layers
    verbose=False
)

# Test generation
prompt = "def fibonacci(n):"
output = llm(prompt, max_tokens=100, temperature=0.7)
print("✓ LLM test successful:")
print(output['choices'][0]['text'])
EOF
```

### Verify Prometheus v0.65-v0.68
```bash
cd ~/workspace/Prometheus_v0_PoC

# Run verification tests
python3 verify_v0_65.py
python3 test_iee_v0_66_direct.py
python3 test_domain_expert_standalone.py
python3 test_generalist_planner_standalone.py
```

All tests should pass (29/29).

---

## Part 7: Create LLM Backend Integration

### Create Local LLM Backend Module
```bash
cd ~/workspace/Prometheus_v0_PoC
```

Create `prometheus/llm_backend_local.py`:

```python
"""
Local LLM Backend for Jetson
Provides unified interface for local model inference
"""

from llama_cpp import Llama
from typing import Optional, Dict, Any
import logging


class LocalLLMBackend:
    """Local LLM backend using llama.cpp"""

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        n_threads: int = 6,
        temperature: float = 0.7,
        top_p: float = 0.9
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Loading model: {model_path}")

        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_threads=n_threads,
            verbose=False
        )

        self.temperature = temperature
        self.top_p = top_p

        self.logger.info("✓ Model loaded successfully")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop: Optional[list] = None
    ) -> str:
        """Generate text from prompt"""

        temp = temperature if temperature is not None else self.temperature
        top = top_p if top_p is not None else self.top_p

        output = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temp,
            top_p=top,
            stop=stop or []
        )

        return output['choices'][0]['text']

    def generate_code_mutation(self, code: str, instruction: str) -> str:
        """Generate mutated code based on instruction"""

        prompt = f"""You are a code mutation engine. Modify the following code according to the instruction.

Original Code:
```python
{code}
```

Instruction: {instruction}

Modified Code:
```python"""

        result = self.generate(prompt, max_tokens=800, temperature=0.8, stop=["```"])
        return result.strip()

    def extract_pattern(self, code: str) -> str:
        """Extract algorithmic pattern from code"""

        prompt = f"""Analyze this code and extract its core algorithmic pattern as a reusable template.

Code:
```python
{code}
```

Pattern Description:
"""

        return self.generate(prompt, max_tokens=400, temperature=0.5)


# Global instance (set in v0.69 demo)
_llm_backend: Optional[LocalLLMBackend] = None


def get_llm_backend() -> LocalLLMBackend:
    """Get global LLM backend instance"""
    if _llm_backend is None:
        raise RuntimeError("LLM backend not initialized. Call set_llm_backend() first.")
    return _llm_backend


def set_llm_backend(backend: LocalLLMBackend):
    """Set global LLM backend instance"""
    global _llm_backend
    _llm_backend = backend
```

Test it:
```python
from prometheus.llm_backend_local import LocalLLMBackend

backend = LocalLLMBackend(
    model_path="~/workspace/models/deepseek-coder/deepseek-coder-6.7b-instruct.Q4_K_M.gguf"
)

code = "def add(a, b): return a + b"
result = backend.generate_code_mutation(code, "Make it handle multiple arguments")
print(result)
```

---

## Part 8: Memory Management Strategy

With 8GB unified memory on Orin Nano:

### Conservative Setup (Recommended)
- OS + System: ~1.5GB
- PyTorch CUDA context: ~0.5GB
- **LLM (4-bit quantized):** ~4-5GB
- **Working memory:** ~2GB

### Model Loading Strategy

**For v0.69 (Code Evolution):**
```python
# Load code generation model once, keep resident
code_llm = LocalLLMBackend(
    model_path="models/deepseek-coder/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
    n_ctx=4096
)
```

**For v0.70 (Multimodal):**
```python
# Unload LLM when running Stable Diffusion
import gc
import torch

# Before loading SD
del code_llm
gc.collect()
torch.cuda.empty_cache()

# Load SD pipeline
from diffusers import StableDiffusionPipeline
pipe = StableDiffusionPipeline.from_pretrained("models/sd-v1-5")
```

**For v0.72 (Meta-learning):**
```python
# Keep smaller LLM resident for pattern extraction
meta_llm = LocalLLMBackend(
    model_path="models/smaller-model.gguf",  # ~3GB
    n_ctx=2048
)
```

---

## Part 9: Performance Optimization

### Enable TensorRT (Optional, Advanced)
```bash
# TensorRT optimizations for faster inference
pip install --upgrade tensorrt
```

### Monitor Resources
```bash
# Install monitoring tools
sudo apt-get install -y htop nvtop

# Monitor GPU usage
watch -n 1 nvidia-smi

# Or use nvtop for better visualization
nvtop
```

### Optimize Swap (if needed)
```bash
# Increase swap for large models
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## Part 10: Ready for v0.69 Development

### Verify Complete Setup Checklist

- [ ] Repository cloned and on v0.19 branch
- [ ] Python virtual environment created
- [ ] PyTorch with CUDA installed
- [ ] llama.cpp installed with GPU support
- [ ] Code generation LLM downloaded (~4GB)
- [ ] All v0.65-v0.68 tests passing
- [ ] LLM backend module created and tested
- [ ] GPU memory verified (8GB available)
- [ ] Can generate text from local LLM

### Next Steps

Once setup is complete:

1. **Implement v0.69:** Create integrated demonstration with real evolutionary loops
2. **Test real evolution:** Use local LLM to mutate agent code
3. **Measure fitness:** Run evolved agents through benchmarks
4. **Visualize progress:** Show fitness improvement over generations

---

## Troubleshooting

### "CUDA out of memory"
- Reduce model size (use Q4_0 instead of Q4_K_M)
- Reduce context length (n_ctx=2048 instead of 4096)
- Clear cache: `torch.cuda.empty_cache()`

### "Slow inference"
- Verify GPU layers: `n_gpu_layers=-1` (use all)
- Check GPU utilization: `nvidia-smi`
- Consider smaller model if consistently slow

### "Model not found"
- Verify path: `ls -lh ~/workspace/models/*/`
- Use absolute path in code
- Check download completed: `du -sh models/`

### "Import errors"
- Activate venv: `source venv_jetson/bin/activate`
- Reinstall: `pip install -r requirements.txt`
- Check Python path: `which python3`

---

## Estimated Timeline

- **Setup (Parts 1-6):** 2-3 hours (including downloads)
- **Testing (Parts 7-8):** 30 minutes
- **Optimization (Part 9):** 30 minutes
- **Ready for development:** 3-4 hours total

---

## Resources

- **Jetson Orin Nano:** https://developer.nvidia.com/embedded/jetson-orin
- **PyTorch for Jetson:** https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048
- **llama.cpp:** https://github.com/ggerganov/llama.cpp
- **Hugging Face:** https://huggingface.co/models
- **Project Prometheus:** https://github.com/pmcray/Prometheus_v0_PoC

---

*Ready to build v0.69-v0.74 with real GPU-accelerated AI!*