
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
            # Use flash for speed/cost efficiency if we do use Gemini
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            print(f"LLMBackend: Using Gemini API (flash).")
        else:
            print(f"LLMBackend: Initializing local model {model_name} on {self.device}...")
            self._init_local_model()

    def _init_local_model(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        # Using 4-bit quantization to ensure it fits easily on Colab T4/L4
        self.local_model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            load_in_4bit=True,
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
            output = self.pipe(messages, max_new_tokens=max_new_tokens, return_full_text=False)
            return output[0]['generated_text'].strip()

# Global singleton for easier access across agents
_backend = None

def get_llm_backend(model_name: str = "microsoft/Phi-3-mini-4k-instruct", force_local: bool = False):
    global _backend
    if _backend is None:
        _backend = LLMBackend(model_name, force_local)
    return _backend
