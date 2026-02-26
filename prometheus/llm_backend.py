import os
import torch
from typing import Optional, List

# Pinned revision of Phi-3-mini-4k-instruct that is compatible with the
# transformers version shipped in Colab (≈4.41).  The July 2024 update
# changed rope_scaling to use "rope_type" instead of "type", which causes
# a KeyError in the cached modeling_phi3.py when using older transformers.
# Revision ff07dc01 is the last stable April-2024 checkpoint.
_PHI3_STABLE_REVISION = "ff07dc01615f8113924aed013115ab2abd32115b"

class LLMBackend:
    """
    Unified backend to switch between Gemini API and Local HuggingFace models.
    """
    def __init__(self, model_name: str = "microsoft/Phi-3-mini-4k-instruct", force_local: bool = False):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self.force_local = force_local
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.local_model = None
        self.tokenizer = None
        
        # Mode selection
        self.use_gemini = self.api_key is not None and not force_local
        self.use_placeholder = False

        if self.use_gemini:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            print(f"LLMBackend: Using Gemini API (flash).")
        elif self.device == "cuda":
            print(f"LLMBackend: Initializing local model {model_name} on {self.device}...")
            self._init_local_model()
        else:
            # Check if we should really load a heavy model on CPU or use a placeholder
            if os.environ.get("PROMETHEUS_FORCE_CPU_MODEL") == "1":
                print(f"LLMBackend: Initializing local model {model_name} on CPU (SLOW)...")
                self._init_local_model()
            else:
                print("LLMBackend: No Gemini API key and no CUDA. Using PLACEHOLDER mode for CI/CD.")
                self.use_placeholder = True

    def _init_local_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig

        # Determine whether to pin a revision.  Only needed for Phi-3-mini
        # to avoid the rope_scaling KeyError introduced in the July 2024 update.
        revision = None
        if self.model_name and "Phi-3-mini-4k-instruct" in self.model_name:
            revision = _PHI3_STABLE_REVISION

        tokenizer_kwargs = dict(trust_remote_code=True)
        if revision:
            tokenizer_kwargs["revision"] = revision

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, **tokenizer_kwargs)

        model_kwargs = dict(
            trust_remote_code=True,
            # Use eager attention to avoid the flash-attention window_size warning
            # that can escalate to an error on some transformers versions.
            attn_implementation="eager",
        )
        if revision:
            model_kwargs["revision"] = revision

        if self.device == "cuda":
            # 4-bit quantization only works on CUDA
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            self.local_model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                quantization_config=bnb_config,
                **model_kwargs,
            )
        else:
            # Fallback for CPU
            print("LLMBackend: CUDA not available, loading model on CPU without quantization (this may be slow and memory-intensive).")
            self.local_model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="cpu",
                torch_dtype=torch.float32,
                **model_kwargs,
            )

        self.pipe = pipeline(
            "text-generation",
            model=self.local_model,
            tokenizer=self.tokenizer,
        )

    def generate(self, prompt: str, max_new_tokens: int = 1024) -> str:
        if self.use_gemini:
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        elif self.use_placeholder:
            # Return a generic but valid response for testing
            return (
                "```python\n"
                "def optimized_function(*args, **kwargs):\n"
                "    # Placeholder response from LLMBackend\n"
                "    pass\n"
                "```"
            )
        else:
            # Local Inference — Phi-3 chat template
            full_prompt = f"<|user|>\n{prompt}<|end|>\n<|assistant|>"
            output = self.pipe(full_prompt, max_new_tokens=max_new_tokens, return_full_text=False)
            return output[0]['generated_text'].strip()

# Global singleton for easier access across agents
_backend = None

def get_llm_backend(model_name: str = "microsoft/Phi-3-mini-4k-instruct", force_local: bool = False):
    global _backend
    if _backend is None:
        _backend = LLMBackend(model_name, force_local)
    return _backend
