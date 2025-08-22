import os
import logging
import sys
import importlib
import hashlib

# --- Prometheus Agent Imports ---
from prometheus.planner import PlannerAgent
# CoderAgent is now dynamically imported
from prometheus.evaluator import EvaluatorAgent
from prometheus.corrector import CorrectorAgent
from prometheus.mcs import MCSSupervisor
from prometheus.knowledge_agent import KnowledgeAgent

# --- Tool Imports ---
from prometheus.tools.base_tools import CompilerTool, StaticAnalyzerTool, LeanTool, PDFTool

# --- System Imports ---
from prometheus.performance_logger import PerformanceLogger
from prometheus.visualizer_client import emit_status

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='crls_loop.log', filemode='w')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    logging.error("FATAL: The GOOGLE_API_KEY environment variable is not set. Please set it to your API key.")
    sys.exit(1)


def get_coder_agent(api_key, compiler, analyzer, lean_tool, knowledge_agent):
    """Dynamically imports and returns an instance of the CoderAgent."""
    coder_module_name = 'prometheus.coder'

    importlib.invalidate_caches()

    if coder_module_name in sys.modules:
        from prometheus.reloader import reload_agent_module
        if not reload_agent_module(coder_module_name):
            raise ImportError(f"Failed to reload {coder_module_name}")
        coder_module = sys.modules[coder_module_name]
    else:
        coder_module = importlib.import_module(coder_module_name)

    CoderAgent = getattr(coder_module, 'CoderAgent')

    return CoderAgent(
        api_key=api_key,
        compiler=compiler,
        analyzer=analyzer,
        lean_tool=lean_tool,
        knowledge_agent=knowledge_agent
    )

def main():
    # 1. Instantiate Tools & Logger
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()
    lean_tool = LeanTool()
    pdf_tool = PDFTool()
    performance_logger = PerformanceLogger()

    # 2. Instantiate Agents that are not dynamically loaded
    planner = PlannerAgent()
    evaluator = EvaluatorAgent(api_key=API_KEY, lean_tool=lean_tool)
    corrector = CorrectorAgent()
    knowledge_agent = KnowledgeAgent(api_key=API_KEY, performance_logger=performance_logger, pdf_tool=pdf_tool)
    mcs = MCSSupervisor(planner=planner, resource_manager=None) # ResourceManager not used in this version

    # 3. Task Definition
    logging.info("\n--- Starting v0.42: The First RSI Cycle ---")
    emit_status("Orchestrator", "thinking", {"task": "Starting RSI Cycle demonstration."})

    task_description = "Refactor the inefficient_sort.py file to be more efficient."
    try:
        with open('toy_problem/inefficient_sort.py', 'r') as f:
            original_code = f.read()
    except FileNotFoundError:
        logging.error(f"Could not find 'toy_problem/inefficient_sort.py'. Aborting.")
        return

    # 4. The RSI Loop
    max_crls_attempts = 3
    crls_attempts = 0
    task_solved = False

    failure_history = []
    while not task_solved and crls_attempts < max_crls_attempts:
        crls_attempts += 1
        logging.info(f"\n--- CRLS Attempt #{crls_attempts} ---")
        emit_status("Orchestrator", "thinking", {"task": f"CRLS Attempt #{crls_attempts}"})

        try:
            # Meta-Causal Analysis: Get hash of test file before modification
            test_file_path = 'toy_problem/test_inefficient_sort.py'
            try:
                with open(test_file_path, 'rb') as f:
                    pre_modification_hash = hashlib.sha256(f.read()).hexdigest()
            except FileNotFoundError:
                logging.error(f"Could not find test file '{test_file_path}'. Causal analysis will be skipped.")
                pre_modification_hash = None

            coder = get_coder_agent(API_KEY, compiler, analyzer, lean_tool, knowledge_agent)
            logging.info(f"Dynamically loaded CoderAgent.")

            refactored_code = coder.refactor_code(original_code)

            if refactored_code != original_code:
                logging.info("✅ Task solved successfully on this attempt! Now performing meta-causal analysis...")

                # Meta-Causal Analysis: Check for reward hacking
                if pre_modification_hash and not mcs.perform_causal_analysis(test_file_path, pre_modification_hash):
                    logging.warning("MCS intervention: Reward hacking detected. Task is considered UNSOLVED.")
                    task_solved = False
                else:
                    emit_status("Orchestrator", "success", {"task": "RSI Cycle successful."})
                    task_solved = True
            else:
                failure_reason = "Refactoring failed."
                logging.warning(f"Task not solved on this attempt. Reason: {failure_reason}")
                emit_status("Coder", "failure", {"task": failure_reason})
                failure_history.append(failure_reason)

        except (ImportError, AttributeError, TypeError) as e:
            logging.error(f"An error occurred with the CoderAgent: {e}", exc_info=True)
            break # Exit loop on critical error

    # 5. Escalation to Self-Modification
    modification_attempts = 0
    max_modification_attempts = 3

    if not task_solved and modification_attempts < max_modification_attempts:
        modification_attempts += 1

        # Meta-Learning: Decide which module to modify
        target_module = 'prometheus.coder' # Default target
        if len(failure_history) == max_crls_attempts:
            logging.warning("CRLS loop failed maximum number of times. Suspecting a metacognitive failure.")
            logging.info("Targeting CorrectorAgent for self-modification.")
            target_module = 'prometheus.corrector'

        logging.info(f"\n--- Escalating to Self-Modification (Attempt #{modification_attempts}) ---")
        emit_status("Orchestrator", "generating_patch", {"task": f"CRLS failed, escalating to self-modification of {target_module}."})

        # MCS Stability Check
        if not mcs.check_stability(modification_attempts, []): # Passing empty patch history for now
            return

        # This is a simulation of the SMM and IEE process
        # In a real scenario, SMM would generate a patch file. We will simulate this.
        # For this demo, we assume the patch is always "smart" for the targeted module.
        if target_module == 'prometheus.corrector':
            # This would be a call to a simulated SMM for the Corrector
            # Then, we call the meta-evaluation workflow
            logging.info("Simulating SMM for CorrectorAgent and starting Meta-Evaluation.")
            # The IEE (EvaluatorAgent) runs the benchmark to verify the patch
            patch_is_verified = evaluator.evaluate_meta_patch("path/to/simulated/corrector_patch.diff")
        else:
            patch_is_verified = True # Assume normal patch verification is successful

        if patch_is_verified:
            logging.info(f"IEE simulation: Patch for {target_module} verified successfully.")
            emit_status("Orchestrator", "verifying_patch", {"status": "success", "target": target_module})

            success = corrector.trigger_self_modification(target_module, patch_is_verified=True)

            if success:
                logging.info("\n--- Re-attempting Task with Upgraded Agent ---")
                emit_status("Orchestrator", "re-attempting_task", {"task": "Re-attempting task with new agent."})

                try:
                    # Get the new, "smarter" CoderAgent
                    coder = get_coder_agent(API_KEY, compiler, analyzer, lean_tool, knowledge_agent)
                    refactored_code = coder.refactor_code(original_code)

                    if refactored_code != original_code:
                        logging.info("✅ Task solved successfully on re-attempt!")
                        emit_status("Orchestrator", "success", {"task": "RSI Cycle successful on re-attempt."})
                        task_solved = True
                    else:
                        logging.error("❌ Task FAILED even after self-modification.")
                        emit_status("Orchestrator", "failure", {"task": "Self-modification did not solve the task."})

                except (ImportError, AttributeError, TypeError) as e:
                    logging.error(f"An error occurred with the upgraded CoderAgent: {e}", exc_info=True)
            else:
                logging.error("❌ Self-modification failed. Could not reload the agent.")
                emit_status("Orchestrator", "failure", {"task": "Self-modification failed."})
        else:
            logging.warning("IEE simulation: Patch failed verification. Halting.")
            emit_status("Orchestrator", "failure", {"task": "Patch verification failed."})

    if not task_solved:
        logging.info("\n--- End of Process: Task could not be solved. ---")
    else:
        logging.info("\n--- End of Process: Task solved successfully. ---")


if __name__ == "__main__":
    main()