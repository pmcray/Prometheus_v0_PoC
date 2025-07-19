
import logging

def verify_imports():
    logging.info("--- Verifying all imports ---")
    try:
        from prometheus.auditor_agent import AuditorAgent
        logging.info("✅ AuditorAgent imported successfully.")
        from prometheus.coder import CoderAgent
        logging.info("✅ CoderAgent imported successfully.")
        from prometheus.corrector import CorrectorAgent
        logging.info("✅ CorrectorAgent imported successfully.")
        from prometheus.evaluator import EvaluatorAgent
        logging.info("✅ EvaluatorAgent imported successfully.")
        from prometheus.gene_archive import GeneArchive
        logging.info("✅ GeneArchive imported successfully.")
        from prometheus.knowledge_agent import KnowledgeAgent
        logging.info("✅ KnowledgeAgent imported successfully.")
        from prometheus.mcs import MCSSupervisor
        logging.info("✅ MCSSupervisor imported successfully.")
        from prometheus.performance_logger import PerformanceLogger
        logging.info("✅ PerformanceLogger imported successfully.")
        from prometheus.planner import PlannerAgent
        logging.info("✅ PlannerAgent imported successfully.")
        from prometheus.proof_tree import ProofTree
        logging.info("✅ ProofTree imported successfully.")
        from prometheus.strategy_archive import StrategyArchive
        logging.info("✅ StrategyArchive imported successfully.")
        from prometheus.system_state import SystemState
        logging.info("✅ SystemState imported successfully.")
        from prometheus.tools import CausalGraphTool
        logging.info("✅ CausalGraphTool imported successfully.")
        from prometheus.toy_chemistry_sim import ToyChemistrySim
        logging.info("✅ ToyChemistrySim imported successfully.")
        from prometheus.agent_templates import HypothesisGenerator
        logging.info("✅ Agent Templates imported successfully.")
        from prometheus.brain_map import BrainMap
        logging.info("✅ BrainMap imported successfully.")
        logging.info("\n--- All imports verified successfully! ---")
    except ImportError as e:
        logging.error(f"❌ Import verification failed: {e}")

if __name__ == "__main__":
    verify_imports()
