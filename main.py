import os
import logging
import sys
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.evaluator import EvaluatorAgent
from src.corrector import CorrectorAgent
from src.mcs import MCSSupervisor
from src.curriculum_agent import CurriculumAgent
from src.tutor import TutorAgent
from src.memory_agent import MemoryAgent
from src.performance_predictor import PerformancePredictorAgent
from src.tools import CompilerTool, StaticAnalyzerTool, LeanTool
from src.system_state import SystemState
from src.performance_logger import PerformanceLogger
from src.visualization_server import VisualizationServer
from src.visualization_client import VisualizationClient

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
    memory_agent = MemoryAgent()

    # 2. Setup Visualization
    vis_server = VisualizationServer()
    vis_server.run_in_background()
    vis_client = VisualizationClient()

    # 3. Instantiate Agents
    predictor = PerformancePredictorAgent()
    planner = PlannerAgent(llm_provider=llm_provider, predictor=predictor)
    coder = CoderAgent(llm_provider=llm_provider, compiler=compiler, analyzer=analyzer, lean_tool=lean_tool)
    evaluator = EvaluatorAgent(memory_agent=memory_agent, llm_provider=llm_provider)
    corrector = CorrectorAgent()
    curriculum_agent = CurriculumAgent(llm_provider=llm_provider, performance_logger=performance_logger)
    tutor = TutorAgent(llm_provider=llm_provider)

    # 4. Instantiate Supervisor
    supervisor = MCSSupervisor(
        planner=planner,
        coder=coder,
        evaluator=evaluator,
        corrector=corrector,
        llm_provider=llm_provider,
        vis_client=vis_client
    )

    # 4. Select and run the appropriate execution mode
    run_mode = os.environ.get("RUN_MODE", "crls").lower()
    logging.info(f"Executing in '{run_mode}' mode.")

    if run_mode == "evolution":
        logging.info("--- Starting Evolution Mode ---")
        target_file = "toy_problem/inefficient_sort.py"
        test_file = "toy_problem/test_inefficient_sort.py"

        if not os.path.exists(target_file) or not os.path.exists(test_file):
            logging.error(f"FATAL: Target files for evolution not found.")
            sys.exit(1)

        fittest_gene = supervisor.run_evolutionary_cycle(
            initial_code_path=target_file,
            test_file_path=test_file,
            generations=5, # Keep it short for testing
            population_size=10
        )
        if fittest_gene:
            logging.info(f"Evolution complete. Fittest gene saved to gene archive.")
        else:
            logging.error("Evolutionary cycle failed to produce a fit gene.")

    elif run_mode == "theorem_proving":
        logging.info("--- Starting Theorem Proving Mode ---")
        num_theorems_to_prove = 3
        for i in range(num_theorems_to_prove):
            logging.info(f"\n--- Theorem Proving Attempt {i+1}/{num_theorems_to_prove} ---")
            theorem = curriculum_agent.generate_theorem()
            if not theorem:
                logging.error("Failed to generate a theorem.")
                continue

            logging.info(f"Generated Theorem: {theorem}")
            proof = coder.prove(theorem)
            if proof:
                logging.info(f"✅ Theorem proven successfully!\nProof:\n{proof}")
            else:
                logging.error("❌ Failed to prove the theorem.")

    elif run_mode == "crls":
        logging.info("\n--- Starting Assembly of Experts Demo (v0.37) ---")

        # 1. Setup a sample task
        problem_file = "toy_problem/loop_problem.py"
        test_file = "toy_problem/test_loop_problem.py"
        goal = "Refactor the 'sum_of_squares' function to be more efficient."

        try:
            with open(problem_file, 'r') as f:
                code_snippet = f.read()
        except FileNotFoundError:
            logging.error(f"Could not find problem file: {problem_file}")
            sys.exit(1)

        # 2. Add a mock LoRA adapter to the GeneArchive
        # In a real scenario, this would be the path to a trained adapter file.
        mock_adapter_path = "/path/to/lora/adapters/loop_optimizer.bin"
        supervisor.gene_archive.add_lora_adapter("LOOP_OPTIMIZATION", mock_adapter_path)

        # 3. Use the PlannerAgent to classify the task and create a plan
        plan = planner.plan(code_snippet, goal)
        logging.info(f"PlannerAgent created plan: {plan}")

        # 4. Run self-modification using the plan
        # The supervisor will now handle the adapter loading based on the plan
        final_code, success = supervisor.run_self_modification(plan, test_file)

        if success:
            logging.info(f"Self-modification successful. Final code:\n{final_code}")
        else:
            logging.error(f"Self-modification failed. Final code:\n{final_code}")

        logging.info("\n--- Assembly of Experts Demo Finished ---")
    else:
        logging.error(f"FATAL: Unknown RUN_MODE '{run_mode}'.")
        sys.exit(1)

if __name__ == "__main__":
    main()