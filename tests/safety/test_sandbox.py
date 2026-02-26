"""
Tests for RuntimeSandbox — WP-03 Verification
"""

import pytest
from prometheus.safety.sandbox import RuntimeSandbox

def test_sandbox_executes_safe_code():
    sandbox = RuntimeSandbox()
    code = """
def add(a, b):
    return a + b
"""
    success, result = sandbox.run_isolated(code, "add", args=(10, 5))
    assert success is True
    assert result == 15

def test_sandbox_catches_infinite_loop():
    # Set a very low CPU limit for quick test
    sandbox = RuntimeSandbox(cpu_time_sec=1)
    code = """
def infinite_loop():
    while True:
        pass
"""
    success, result = sandbox.run_isolated(code, "infinite_loop")
    assert success is False
    # Either my timeout or the OS SIGXCPU (return code -24)
    assert "Timeout" in str(result) or "return code -24" in str(result)

def test_sandbox_prevents_file_writing():
    sandbox = RuntimeSandbox()
    code = """
import os
def write_file():
    # Attempt to write a large file that exceeds the 1MB limit
    with open("malicious.txt", "w") as f:
        f.write("A" * (2 * 1024 * 1024))
    return True
"""
    success, result = sandbox.run_isolated(code, "write_file")
    assert success is False
    assert "OSError" in result or "return code" in str(result)

def test_sandbox_enforces_memory_limit():
    # Small 10MB limit
    sandbox = RuntimeSandbox(memory_limit_mb=10)
    code = """
def memory_hog():
    # Attempt to allocate 50MB
    data = bytearray(50 * 1024 * 1024)
    return len(data)
"""
    success, result = sandbox.run_isolated(code, "memory_hog")
    assert success is False
    assert "MemoryError" in result or "Memory" in result or "Traceback" in result
