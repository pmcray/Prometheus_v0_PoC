"""
Runtime Sandbox — Prometheus v0.98 (WP-03)

Provides isolated execution for dynamically generated code using 
subprocess and resource limits.
"""

import subprocess
import sys
import os
import tempfile
import traceback
import resource
import time
import pickle
import base64
from typing import Any, Callable, Dict, Optional, Tuple

class RuntimeSandbox:
    """
    Executes Python code in an isolated process with restricted resources.
    """
    def __init__(self, memory_limit_mb: int = 1024, cpu_time_sec: int = 5):
        self.memory_limit = memory_limit_mb * 1024 * 1024
        self.cpu_time = cpu_time_sec

    def run_isolated(self, code: str, func_name: str, args: Tuple = (), kwargs: Dict = {}) -> Tuple[bool, Any]:
        """
        Runs the provided code in a separate process and returns (success, result/error).
        """
        # We use a wrapper script to handle execution and serialization
        wrapper_template = """
import sys
import pickle
import base64
import resource
import traceback

def set_limits(cpu, mem):
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        # Address space limit
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        # File size limit (1MB)
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024*1024, 1024*1024))
    except:
        pass

def main():
    cpu_limit = {cpu_limit}
    mem_limit = {mem_limit}
    func_name = "{func_name}"
    
    # Apply limits
    set_limits(cpu_limit, mem_limit)
    
    try:
        # Load code
        code = \"\"\"{code_escaped}\"\"\"
        
        local_scope = {{}}
        exec(code, {{"__builtins__": __builtins__}}, local_scope)
        
        func = local_scope.get(func_name)
        if not func or not callable(func):
            # Fallback to first callable
            found = [v for v in local_scope.values() if callable(v)]
            if found:
                func = found[0]
            else:
                print("ERR: No callable found")
                return

        # Load args
        args = pickle.loads(base64.b64decode("{args_b64}"))
        kwargs = pickle.loads(base64.b64decode("{kwargs_b64}"))
        
        # Execute
        result = func(*args, **kwargs)
        
        # Return result
        print("RESULT:" + base64.b64encode(pickle.dumps(result)).decode())
        
    except Exception as e:
        print("ERROR:" + base64.b64encode(pickle.dumps(traceback.format_exc())).decode())

if __name__ == "__main__":
    main()
"""
        # Escape code for the triple-quoted string
        code_escaped = code.replace('\\', '\\\\').replace('"', '\\"').replace("'''", "\\'\\'\\'")
        
        # Encode arguments
        args_b64 = base64.b64encode(pickle.dumps(args)).decode()
        kwargs_b64 = base64.b64encode(pickle.dumps(kwargs)).decode()
        
        wrapper_script = wrapper_template.format(
            cpu_limit=self.cpu_time,
            mem_limit=self.memory_limit,
            func_name=func_name,
            code_escaped=code_escaped,
            args_b64=args_b64,
            kwargs_b64=kwargs_b64
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
            tf.write(wrapper_script)
            temp_name = tf.name
            
        try:
            # Run the subprocess
            proc = subprocess.run(
                [sys.executable, temp_name],
                capture_output=True,
                text=True,
                timeout=self.cpu_time + 5
            )
            
            # Parse output
            for line in proc.stdout.splitlines():
                if line.startswith("RESULT:"):
                    res_b64 = line[len("RESULT:"):]
                    return True, pickle.loads(base64.b64decode(res_b64))
                if line.startswith("ERROR:"):
                    err_b64 = line[len("ERROR:"):]
                    return False, pickle.loads(base64.b64decode(err_b64))
            
            if proc.returncode != 0:
                return False, f"Process failed with return code {proc.returncode}\n{proc.stderr}"
                
            return False, "No result found in subprocess output."
            
        except subprocess.TimeoutExpired:
            return False, "Sandbox Timeout: Code execution exceeded time limit."
        except Exception as e:
            return False, f"Sandbox Internal Error: {str(e)}"
        finally:
            if os.path.exists(temp_name):
                os.remove(temp_name)
