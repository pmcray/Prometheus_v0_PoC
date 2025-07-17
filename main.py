
import os
import logging
import sys
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.evaluator import EvaluatorAgent
from src.corrector import CorrectorAgent
from src.mcs import MCSSupervisor
from src.benchmark_agent import BenchmarkAgent
from src.tools import CompilerTool, StaticAnalyzerTool

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='crls_loop.log',
    filemode='w'
)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

def main():
    # 1. Instantiate Tools
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()

    # 2. Instantiate Agents
    planner = PlannerAgent()
    coder = CoderAgent(api_key=API_KEY, compiler=compiler, analyzer=analyzer)
    evaluator = EvaluatorAgent()
    corrector = CorrectorAgent()
    benchmark_agent = BenchmarkAgent(api_key=API_KEY)

    # 3. Instantiate Supervisor
    supervisor = MCSSupervisor(planner, coder, evaluator, corrector)

    # 4. Run the self-modification loop
    logging.info("--- Running Self-Modification Task ---")
    supervisor.run_self_modification()
    
    # 5. Run the benchmark generation task
    logging.info("\n--- Running Benchmark Generation Task ---")
    function_name, function_code, test_code = benchmark_agent.generate_benchmark()
    
    if function_name and function_code and test_code:
        function_filename = f"toy_problem/{function_name}.py"
        test_filename = f"toy_problem/test_{function_name}.py"
        
        with open(function_filename, 'w') as f:
            f.write(function_code)
        with open(test_filename, 'w') as f:
            f.write(test_code)
            
        logging.info(f"Successfully created new benchmark files: {function_filename} and {test_filename}")
        
        # Verify the new benchmark
        logging.info("Verifying the new benchmark by running its tests...")
        import subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = f".{os.pathsep}toy_problem"
        result = subprocess.run([sys.executable, "-m", "pytest", test_filename], capture_output=True, text=True, env=env)
        
        if result.returncode == 0:
            logging.info("✅ New benchmark is valid and all tests passed!")
        else:
            logging.error("❌ New benchmark is invalid. Tests did not pass.")
            logging.error(result.stdout)
            logging.error(result.stderr)


if __name__ == "__main__":
    main()
