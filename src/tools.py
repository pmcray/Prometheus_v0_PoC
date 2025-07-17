
import subprocess
import sys
import logging
from py_compile import PyCompileError, compile

class Tool:
    def use(self, file_path):
        raise NotImplementedError

class CompilerTool(Tool):
    def use(self, file_path):
        """
        Compiles a Python file and returns any errors.
        """
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
        """
        Runs a static analyzer (pyflakes) on a Python file and returns the output.
        """
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
