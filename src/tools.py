import subprocess
import sys
import logging
from py_compile import PyCompileError, compile
import os

class Tool:
    def use(self, file_path):
        raise NotImplementedError

class CompilerTool(Tool):
    def use(self, file_path):
        logging.info(f"CompilerTool: Compiling {file_path} within the sandbox.")
        try:
            compile(file_path, doraise=True)
            logging.info(f"CompilerTool: {file_path} compiled successfully.")
            return None
        except PyCompileError as e:
            logging.warning(f"CompilerTool: Compilation failed for {file_path}.")
            return str(e)

class StaticAnalyzerTool(Tool):
    def use(self, file_path):
        logging.info(f"StaticAnalyzerTool: Analyzing {file_path} with pyflakes within the sandbox.")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pyflakes", file_path],
                capture_output=True,
                text=True,
                check=True
            )
            logging.info(f"StaticAnalyzerTool: {file_path} passed static analysis.")
            return None
        except subprocess.CalledProcessError as e:
            logging.warning(f"StaticAnalyzerTool: Static analysis found issues in {file_path}.")
            return e.stdout

class LeanTool(Tool):
    def use(self, lean_code):
        """
        Checks a snippet of Lean code for correctness.
        """
        logging.info("LeanTool: Checking Lean code.")
        temp_lean_file = "temp_proof.lean"
        with open(temp_lean_file, 'w') as f:
            f.write(lean_code)
        
        try:
            # Add elan to the path
            env = os.environ.copy()
            env["PATH"] = f"{os.path.expanduser('~')}/.elan/bin:{env['PATH']}"
            
            result = subprocess.run(
                ["lean", temp_lean_file],
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            logging.info("LeanTool: Lean code is valid.")
            return None
        except subprocess.CalledProcessError as e:
            logging.warning("LeanTool: Lean code is invalid.")
            return e.stderr
        finally:
            os.remove(temp_lean_file)