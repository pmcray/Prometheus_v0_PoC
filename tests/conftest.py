"""
Shared pytest fixtures for the Prometheus test suite.

Key responsibilities
--------------------
1. Auto-mock the LLM backend so tests that instantiate CausalAttentionWrapper,
   PlannerAgent, or any other class that calls get_llm_backend() do not attempt
   to download or load a local HuggingFace model.  The mock backend:
     - returns deterministic canned text
     - is available as the ``mock_llm_backend`` fixture for tests that need to
       inspect calls or change the return value
2. Reset the global LLM backend singleton before every test so fixture ordering
   does not matter.
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# LLM backend mock
# ---------------------------------------------------------------------------

_DEFAULT_LLM_RESPONSE = (
    "```python\n"
    "def optimized(n):\n"
    "    return n * (n + 1) // 2\n"
    "```"
)


@pytest.fixture(autouse=True)
def mock_llm_backend(monkeypatch):
    """
    Auto-applied fixture: replaces the global LLM backend singleton with a
    lightweight MagicMock for every test.

    The mock backend exposes:
        backend.generate(prompt) -> str   (returns ``_DEFAULT_LLM_RESPONSE``)
        backend.use_gemini       -> False
        backend.api_key          -> None

    Tests that need a specific response can overwrite ``generate.return_value``::

        def test_something(mock_llm_backend):
            mock_llm_backend.generate.return_value = "my custom response"
            ...
    """
    import prometheus.llm_backend as llm_mod

    backend = MagicMock(name="LLMBackend-mock")
    backend.generate.return_value = _DEFAULT_LLM_RESPONSE
    backend.use_gemini = False
    backend.api_key = None

    # Reset the module-level singleton so each test starts clean.
    monkeypatch.setattr(llm_mod, "_backend", None)

    # Patch get_llm_backend to return our mock and avoid any model loading.
    monkeypatch.setattr(llm_mod, "get_llm_backend", lambda *a, **kw: backend)

    # Also patch the class constructor in case a module cached a direct import.
    monkeypatch.setattr(llm_mod, "LLMBackend", lambda *a, **kw: backend)

    return backend
