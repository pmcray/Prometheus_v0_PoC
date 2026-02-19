import os
import torch
from typing import Optional, List

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
        self.use_gemini = self.api_key is not None and not force_local

        if self.use_gemini:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            print(f"LLMBackend: Using Gemini API (flash).")
        else:
            print(f"LLMBackend: Initializing local model {model_name} on {self.device}...")
            self._init_local_model()

    def _init_local_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        
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
                trust_remote_code=True
            )
        else:
            # Fallback for CPU
            print("LLMBackend: CUDA not available, loading model on CPU without quantization (this may be slow and memory-intensive).")
            self.local_model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="cpu",
                torch_dtype=torch.float32,
                trust_remote_code=True
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
        else:
            # Local Inference
            messages = [{"role": "user", "content": prompt}]
            # Phi-3 prompt template
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
