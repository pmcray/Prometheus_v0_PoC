"""
Unified LLM backend supporting both local (Ollama) and cloud (Gemini) models.
Prioritizes local GPU-accelerated inference on Jetson hardware.
"""

import os
import logging
from typing import Optional, Dict, Any
import google.generativeai as genai

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logging.warning("Ollama not installed. Install with: pip install ollama")


class LLMBackend:
    """
    Unified interface for LLM inference.
    Automatically selects best available backend (Ollama > Gemini).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        prefer_local: bool = True,
        ollama_model: str = "deepseek-coder:6.7b-instruct-q4_K_M",
        gemini_model: str = "gemini-1.5-flash",
        ollama_host: str = "http://localhost:11434"
    ):
        """
        Initialize LLM backend with fallback capabilities.

        Args:
            api_key: Google Gemini API key (optional if using Ollama)
            prefer_local: Use Ollama if available (True recommended for Jetson)
            ollama_model: Ollama model name
            gemini_model: Gemini model name (fallback)
            ollama_host: Ollama server URL
        """
        self.prefer_local = prefer_local
        self.ollama_model = ollama_model
        self.gemini_model = gemini_model
        self.ollama_host = ollama_host

        # Try to set up Ollama first
        self.ollama_available = False
        if OLLAMA_AVAILABLE and prefer_local:
            try:
                # Test Ollama connection
                ollama.list()
                self.ollama_available = True
                logging.info(f"✓ Ollama available - using local model: {ollama_model}")
            except Exception as e:
                logging.warning(f"Ollama unavailable: {e}")

        # Set up Gemini fallback
        self.gemini_available = False
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.gemini_model_obj = genai.GenerativeModel(gemini_model)
                self.gemini_available = True
                logging.info(f"✓ Gemini available - fallback model: {gemini_model}")
            except Exception as e:
                logging.warning(f"Gemini unavailable: {e}")

        # Determine active backend
        if self.ollama_available:
            self.active_backend = "ollama"
            logging.info("🚀 Using LOCAL Ollama (GPU-accelerated)")
        elif self.gemini_available:
            self.active_backend = "gemini"
            logging.info("☁️  Using CLOUD Gemini (fallback)")
        else:
            raise RuntimeError("No LLM backend available! Install Ollama or provide Gemini API key.")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text using the active backend.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Backend-specific parameters

        Returns:
            Generated text
        """
        if self.active_backend == "ollama":
            return self._generate_ollama(prompt, temperature, max_tokens, **kwargs)
        elif self.active_backend == "gemini":
            return self._generate_gemini(prompt, temperature, max_tokens, **kwargs)
        else:
            raise RuntimeError("No active LLM backend")

    def _generate_ollama(
        self,
        prompt: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> str:
        """Generate using local Ollama model."""
        try:
            options = {
                "temperature": temperature,
            }
            if max_tokens:
                options["num_predict"] = max_tokens

            response = ollama.generate(
                model=self.ollama_model,
                prompt=prompt,
                options=options,
                **kwargs
            )
            return response['response']
        except Exception as e:
            logging.error(f"Ollama generation failed: {e}")
            if self.gemini_available:
                logging.info("Falling back to Gemini...")
                self.active_backend = "gemini"
                return self._generate_gemini(prompt, temperature, max_tokens, **kwargs)
            raise

    def _generate_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> str:
        """Generate using cloud Gemini model."""
        try:
            generation_config = {
                "temperature": temperature,
            }
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens

            response = self.gemini_model_obj.generate_content(
                prompt,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            logging.error(f"Gemini generation failed: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get backend statistics."""
        return {
            "active_backend": self.active_backend,
            "ollama_available": self.ollama_available,
            "ollama_model": self.ollama_model if self.ollama_available else None,
            "gemini_available": self.gemini_available,
            "gemini_model": self.gemini_model if self.gemini_available else None,
        }


# Global singleton for easy access
_global_backend: Optional[LLMBackend] = None


def get_llm_backend(
    api_key: Optional[str] = None,
    prefer_local: bool = True,
    **kwargs
) -> LLMBackend:
    """
    Get or create global LLM backend.

    Args:
        api_key: Gemini API key (optional)
        prefer_local: Prefer Ollama over Gemini
        **kwargs: Additional backend configuration

    Returns:
        LLMBackend instance
    """
    global _global_backend
    if _global_backend is None:
        _global_backend = LLMBackend(
            api_key=api_key,
            prefer_local=prefer_local,
            **kwargs
        )
    return _global_backend


def set_llm_backend(backend: LLMBackend):
    """Set global LLM backend."""
    global _global_backend
    _global_backend = backend
