import os
import logging
import sys
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.evaluator import EvaluatorAgent
from src.corrector import CorrectorAgent
from src.mcs import MCSSupervisor
from src.curriculum_agent import CurriculumAgent
from src.tools import CompilerTool, StaticAnalyzerTool, LeanTool
from src.system_state import SystemState
from src.performance_logger import PerformanceLogger

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='crls_loop.log', filemode='w')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)
# ---------------------

from src.llm_provider import GoogleGeminiProvider, OllamaPhi3Provider, MockProvider

def setup_llm_provider():
    """
    Selects and instantiates the appropriate LLM provider based on environment variables.
    """
    provider_name = os.environ.get("LLM_PROVIDER", "mock").lower()

    if provider_name == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logging.error("FATAL: LLM_PROVIDER is 'google' but GOOGLE_API_KEY is not set.")
            sys.exit(1)
        return GoogleGeminiProvider(api_key=api_key)

    elif provider_name == "phi3":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaPhi3Provider(base_url=base_url)

    elif provider_name == "mock":
        return MockProvider()

    else:
        logging.error(f"FATAL: Unknown LLM_PROVIDER '{provider_name}'.")
        sys.exit(1)

def main():
    # 1. Instantiate Tools, Logger and LLM Provider
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()
    lean_tool = LeanTool()
    performance_logger = PerformanceLogger()
    llm_provider = setup_llm_provider()

    # 2. Instantiate Agents
    planner = PlannerAgent()
    coder = CoderAgent(llm_provider=llm_provider, compiler=compiler, analyzer=analyzer, lean_tool=lean_tool)
    evaluator = EvaluatorAgent()
    corrector = CorrectorAgent()
    curriculum_agent = CurriculumAgent(llm_provider=llm_provider, performance_logger=performance_logger)

    # 3. Instantiate Supervisor
    supervisor = MCSSupervisor(
        planner=planner,
        coder=coder,
        evaluator=evaluator,
        corrector=corrector
    )

    # 4. Run the main CRLS loop (v0.21)
    logging.info("\n--- Starting CRLS Loop (v0.21) ---")
    num_curriculum_cycles = 3
    benchmark_dir = "benchmarks"
    os.makedirs(benchmark_dir, exist_ok=True)

    for i in range(num_curriculum_cycles):
        logging.info(f"\n--- Curriculum Cycle {i+1}/{num_curriculum_cycles} ---")

        # a. Generate a new benchmark
        benchmark_name, function_code, test_code = curriculum_agent.generate_benchmark()
        if not all([benchmark_name, function_code, test_code]):
            logging.error("Failed to generate a valid benchmark. Ending CRLS loop.")
            break

        logging.info(f"Generated benchmark: {benchmark_name}")

        # b. Save benchmark to files
        function_file_path = os.path.join(benchmark_dir, f"{benchmark_name}.py")
        test_file_path = os.path.join(benchmark_dir, f"test_{benchmark_name}.py")

        with open(function_file_path, 'w') as f:
            f.write(function_code)
        with open(test_file_path, 'w') as f:
            f.write(test_code)

        # c. Run self-modification on the new benchmark
        final_code, success = supervisor.run_self_modification(
            initial_code_path=function_file_path,
            test_file_path=test_file_path
        )

        # d. Log the result
        if final_code:
            complexity = evaluator.analyze_complexity(final_code)
            performance_logger.log_benchmark(
                benchmark_name=benchmark_name,
                success=success,
                complexity=complexity,
                solution_code=final_code if success else function_code # Log the improved code if successful
            )
        else:
            logging.error(f"Supervisor failed to return code for benchmark {benchmark_name}.")

    logging.info("\n--- CRLS Loop Finished ---")

if __name__ == "__main__":
    main()