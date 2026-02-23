import pytest
import os
import shutil

class SystemAuditor:
    """
    Simulate the physical constraint where an agent
    is monitored for unauthorized system calls.
    """
    def __init__(self, allowed_calls):
        self.allowed_calls = allowed_calls
        self.violations = []

    def audit_call(self, call_name, params):
        if call_name not in self.allowed_calls:
            self.violations.append(f"Unauthorized call: {call_name}")
            return False
        return True

@pytest.fixture
def temp_sandbox():
    """Setup a temporary sandbox directory for safety testing."""
    sandbox_dir = os.path.join(os.getcwd(), "test_sandbox")
    os.makedirs(sandbox_dir, exist_ok=True)
    yield sandbox_dir
    shutil.rmtree(sandbox_dir)

def is_safe_path(path, sandbox_root):
    """
    Simulated implementation of a safety layer's path check.
    Ensures that any file access is confined to the sandbox_root.
    """
    absolute_path = os.path.abspath(os.path.join(sandbox_root, path))
    return absolute_path.startswith(sandbox_root)

def test_sandbox_path_verification(temp_sandbox):
    # Valid internal paths
    assert is_safe_path("data/log.txt", temp_sandbox) is True
    assert is_safe_path("src/agent.py", temp_sandbox) is True
    
    # Invalid external paths (Path Traversal)
    assert is_safe_path("../secret.txt", temp_sandbox) is False
    assert is_safe_path("../../etc/passwd", temp_sandbox) is False
    assert is_safe_path("/etc/passwd", temp_sandbox) is False

def test_body_agent_capability_constraint():
    """
    Simulate the constraint of a 'Body' agent (local FM).
    """
    # Define allowed capabilities for the local model (Body)
    allowed_capabilities = ["read_local_file", "write_local_file", "calculate_ast"]
    auditor = SystemAuditor(allowed_capabilities)
    
    # Authorized action
    assert auditor.audit_call("read_local_file", {"path": "src/main.py"}) is True
    
    # Unauthorized action (Physical Constraint Violation)
    assert auditor.audit_call("curl_external_url", {"url": "http://malicious.com"}) is False
    assert len(auditor.violations) == 1
    assert "curl_external_url" in auditor.violations[0]

def test_mind_body_safety_handoff():
    """
    Simulate the handoff where the 'Mind' (Gemini) suggests an action,
    and the 'Body' (local Auditor) verifies it before execution.
    """
    
    def process_request(request, auditor):
        # The 'Mind' (Gemini) generates the request string
        if auditor.audit_call(request['action'], request['params']):
            return f"Action {request['action']} executed safely."
        else:
            return "SAFETY VIOLATION: Action blocked."

    allowed = ["write_result"]
    auditor = SystemAuditor(allowed)
    
    # Mind suggests a safe action
    safe_req = {"action": "write_result", "params": {"data": "Success"}}
    assert "executed safely" in process_request(safe_req, auditor)
    
    # Mind suggests an unsafe action (potentially malicious)
    unsafe_req = {"action": "delete_all_files", "params": {"path": "/"}}
    assert "SAFETY VIOLATION" in process_request(unsafe_req, auditor)
