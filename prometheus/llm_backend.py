"""
Unified LLM backend supporting both local (Ollama) and cloud API models.
Prioritizes local GPU-accelerated inference on Jetson hardware.
"""

import os
import logging
from typing import Optional, Dict, Any

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logging.warning("Ollama not installed. Install with: pip install ollama")


class LLMBackend:
    """
    Unified interface for LLM inference.
    Automatically selects best available backend (Ollama > Cloud API).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        prefer_local: bool = True,
        ollama_model: str = "deepseek-coder:6.7b-instruct-q4_K_M",
        cloud_model: str = "generic-fm-v1",
        ollama_host: str = "http://localhost:11434",
        cloud_api_url: Optional[str] = None
    ):
        """
        Initialize LLM backend with fallback capabilities.

        Args:
            api_key: Cloud API key (optional if using Ollama)
            prefer_local: Use Ollama if available (True recommended for Jetson)
            ollama_model: Ollama model name
            cloud_model: Cloud foundation model name (fallback)
            ollama_host: Ollama server URL
            cloud_api_url: Cloud API endpoint URL
        """
        self.prefer_local = prefer_local
        self.ollama_model = ollama_model
        self.cloud_model = cloud_model
        self.ollama_host = ollama_host
        self.cloud_api_url = cloud_api_url
        self.api_key = api_key

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

        # Set up cloud API fallback (generic mock)
        self.cloud_available = False
        if api_key and cloud_api_url:
            # In a real implementation, this would test the cloud API connection
            # For now, we just mark it as available if credentials are provided
            self.cloud_available = True
            logging.info(f"✓ Cloud API configured - fallback model: {cloud_model}")
        elif api_key:
            # API key provided but no URL - create mock fallback
            self.cloud_available = True
            logging.info(f"✓ Cloud API (mock) - fallback model: {cloud_model}")

        # Determine active backend
        if self.ollama_available:
            self.active_backend = "ollama"
            logging.info("🚀 Using LOCAL Ollama (GPU-accelerated)")
        elif self.cloud_available:
            self.active_backend = "cloud"
            logging.info("☁️  Using CLOUD API (fallback)")
        else:
            raise RuntimeError("No LLM backend available! Install Ollama or provide Cloud API credentials.")

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
        elif self.active_backend == "cloud":
            return self._generate_cloud(prompt, temperature, max_tokens, **kwargs)
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
            if self.cloud_available:
                logging.info("Falling back to Cloud API...")
                self.active_backend = "cloud"
                return self._generate_cloud(prompt, temperature, max_tokens, **kwargs)
            raise

    def _generate_cloud(
        self,
        prompt: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> str:
        """
        Generate using cloud API (generic mock implementation).

        In a real implementation, this would make HTTP requests to a cloud FM API.
        For now, returns a mock response indicating the cloud backend is called.
        """
        try:
            # Mock implementation - in production, this would call a real cloud API
            # Example structure:
            # import requests
            # headers = {"Authorization": f"Bearer {self.api_key}"}
            # payload = {
            #     "model": self.cloud_model,
            #     "prompt": prompt,
            #     "temperature": temperature,
            #     "max_tokens": max_tokens or 2048
            # }
            # response = requests.post(self.cloud_api_url, json=payload, headers=headers)
            # return response.json()["text"]

            logging.warning("Cloud API called but using mock response (no real API configured)")
            return f"[MOCK CLOUD RESPONSE] Generated response for prompt of length {len(prompt)} chars using {self.cloud_model}"
        except Exception as e:
            logging.error(f"Cloud API generation failed: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get backend statistics."""
        return {
            "active_backend": self.active_backend,
            "ollama_available": self.ollama_available,
            "ollama_model": self.ollama_model if self.ollama_available else None,
            "cloud_available": self.cloud_available,
            "cloud_model": self.cloud_model if self.cloud_available else None,
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
        api_key: Cloud API key (optional)
        prefer_local: Prefer Ollama over Cloud API
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
