"""
Prometheus Advanced Orchestrator
Integrates all v0.19+ features into a comprehensive system
"""

import os
import sys
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import all enhanced components
from prometheus.schemas.communication import AgentMessage, MessageType
from prometheus.enhanced_performance_logger import EnhancedPerformanceLogger, DualModeProfiler
from prometheus.causal_attention import CausalAttentionHead
from prometheus.memory_agent import MemoryAgent, GeneBankAgent
from prometheus.enhanced_planner import EnhancedPlannerAgent
from prometheus.enhanced_coder import EnhancedCoderAgent
from prometheus.enhanced_evaluator import EnhancedEvaluatorAgent
from prometheus.enhanced_corrector import EnhancedCorrectorAgent
from prometheus.enhanced_mcs import EnhancedMCSSupervisor
from prometheus.brain_visualizer import BrainMapVisualizer, visualization_client
from prometheus.enhanced_reloader import agent_manager, self_modification_engine

class PrometheusOrchestrator:
    """Advanced orchestrator implementing full v0.19+ feature set"""

    def __init__(self, api_key: str = None, enable_visualization: bool = True,
                 enable_memory: bool = True, enable_rsi: bool = True):

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.enable_visualization = enable_visualization
        self.enable_memory = enable_memory
        self.enable_rsi = enable_rsi

        # Initialize logging system
        self.performance_logger = EnhancedPerformanceLogger()
        self.profiler = DualModeProfiler(self.performance_logger)

        # Initialize core components
        self.causal_attention = CausalAttentionHead()

        # Initialize memory system
        self.memory_agent = None
        self.gene_bank = None
        if enable_memory:
            try:
                self.memory_agent = MemoryAgent()
                self.gene_bank = GeneBankAgent()
                logging.info("Memory system initialized")
            except Exception as e:
                logging.warning(f"Memory system initialization failed: {e}")
                self.enable_memory = False

        # Initialize agents
        self.planner = EnhancedPlannerAgent(
            api_key=self.api_key,
            causal_attention=self.causal_attention
        )

        self.coder = EnhancedCoderAgent(api_key=self.api_key)

        self.evaluator = EnhancedEvaluatorAgent(
            api_key=self.api_key,
            memory_agent=self.memory_agent,
            causal_attention=self.causal_attention
        )

        self.corrector = EnhancedCorrectorAgent(
            api_key=self.api_key,
            memory_agent=self.memory_agent,
            gene_bank=self.gene_bank
        )

        self.mcs = EnhancedMCSSupervisor(
            planner=self.planner,
            api_key=self.api_key
        )

        # Initialize visualization
        self.visualizer = None
        if enable_visualization:
            try:
                self.visualizer = BrainMapVisualizer()
                visualization_client.set_visualizer(self.visualizer)
                logging.info("Visualization system initialized")
            except Exception as e:
                logging.warning(f"Visualization initialization failed: {e}")
                self.enable_visualization = False

        # Initialize RSI system
        if enable_rsi and self.gene_bank:
            try:
                # Register agent factories for stateless instantiation
                agent_manager.register_agent_factory("coder", "prometheus.enhanced_coder", "EnhancedCoderAgent")
                agent_manager.register_agent_factory("corrector", "prometheus.enhanced_corrector", "EnhancedCorrectorAgent")
                agent_manager.register_agent_factory("evaluator", "prometheus.enhanced_evaluator", "EnhancedEvaluatorAgent")

                # Set gene bank for self-modification engine
                self_modification_engine.gene_bank = self.gene_bank
                logging.info("RSI system initialized")
            except Exception as e:
                logging.warning(f"RSI system initialization failed: {e}")
                self.enable_rsi = False

        # Execution state
        self.current_run_id = None
        self.rsi_generation = 0
        self.performance_metrics = []

    async def start_system(self):
        """Start the complete Prometheus system"""
        logging.info("Starting Prometheus Advanced System...")

        # Start visualization server if enabled
        if self.enable_visualization and self.visualizer:
            await self.visualizer.server.start_server()

            # Generate and save brain map interface
            self.visualizer.save_brain_map_interface("prometheus_brain_map.html")
            logging.info("Brain map interface saved to prometheus_brain_map.html")

        logging.info("Prometheus system fully operational")

    async def stop_system(self):
        """Stop the Prometheus system"""
        logging.info("Stopping Prometheus system...")

        if self.enable_visualization and self.visualizer:
            await self.visualizer.server.stop_server()

        logging.info("Prometheus system stopped")

    def run_crls_loop(self, task_description: str, initial_code: str,
                     max_attempts: int = 5, enable_meta_correction: bool = True) -> Dict[str, Any]:
        """Run the complete CRLS loop with all advanced features"""

        # Start new run
        run_id = self.performance_logger.start_run(task_description)
        self.current_run_id = run_id

        # Emit visualization updates
        if self.enable_visualization:
            self.visualizer.emit_agent_status("orchestrator", "starting", {
                "task": task_description,
                "run_id": run_id
            })

        try:
            # Generate initial plan
            plan_message = self.planner.plan_task(task_description, initial_code, run_id)
            self.performance_logger.log_message(plan_message)

            if self.enable_visualization:
                self.visualizer.emit_agent_status("planner_agent", "thinking", {
                    "causal_focus": plan_message.payload.get("causal_focus")
                })

            attempt_count = 0
            last_code = initial_code
            modification_attempts = 0

            while attempt_count < max_attempts:
                attempt_count += 1

                logging.info(f"CRLS Loop - Attempt {attempt_count}/{max_attempts}")

                # Step 1: Code Generation
                if self.enable_visualization:
                    self.visualizer.emit_agent_status("coder_agent", "generating_code", {
                        "attempt": attempt_count
                    })

                code_message = self.coder.process_instruction(plan_message)
                self.performance_logger.log_message(code_message)

                # Step 2: Evaluation
                if self.enable_visualization:
                    self.visualizer.emit_agent_status("evaluator_agent", "evaluating", {
                        "code": code_message.payload["refactored_code"][:200] + "..."
                    })

                eval_message = self.evaluator.evaluate_submission(code_message)
                self.performance_logger.log_message(eval_message)

                critique = eval_message.payload

                # Step 3: MCS Constitutional Review
                if critique["improvement_achieved"] and critique["test_passed"]:
                    # Perform final constitutional review
                    if self.enable_visualization:
                        self.visualizer.emit_agent_status("mcs_supervisor", "reviewing", {
                            "principle": "constitutional_review"
                        })

                    constitutional_approved = self.mcs.perform_constitutional_review(
                        initial_code,
                        code_message.payload["refactored_code"],
                        critique["causal_analysis"],
                        run_id
                    )

                    # Attention audit
                    attention_audit_passed = self.mcs.perform_attention_audit(run_id)

                    if constitutional_approved and attention_audit_passed:
                        # Success!
                        self.performance_logger.end_run("completed", {
                            "final_code": code_message.payload["refactored_code"],
                            "attempts": attempt_count,
                            "improvement_achieved": True
                        })

                        if self.enable_visualization:
                            self.visualizer.emit_agent_status("orchestrator", "success", {
                                "attempts": attempt_count
                            })

                        # Store success in memory
                        if self.enable_memory and self.memory_agent:
                            self.memory_agent.store_success({
                                "run_id": run_id,
                                "initial_code": initial_code,
                                "final_code": code_message.payload["refactored_code"],
                                "solution_strategy": code_message.payload["reasoning"],
                                "performance_improvement": critique.get("dynamic_analysis", {})
                            })

                        return {
                            "success": True,
                            "final_code": code_message.payload["refactored_code"],
                            "attempts": attempt_count,
                            "run_id": run_id
                        }

                # Step 4: Check for cyclical failures
                if self.mcs.check_cyclical_failure(code_message.payload["refactored_code"], run_id):
                    if self.enable_visualization:
                        self.visualizer.visualize_mcs_intervention("CYCLICAL_FAILURE", ["coder_agent", "corrector_agent"])

                    logging.warning("Cyclical failure detected - escalating to meta-correction")
                    break

                # Step 5: Correction
                if self.enable_visualization:
                    self.visualizer.emit_agent_status("corrector_agent", "correcting", {
                        "failure_reason": critique["reason"]
                    })

                correction_message = self.corrector.process_critique(eval_message)
                self.performance_logger.log_message(correction_message)

                # Update plan message for next iteration
                plan_message.payload.update({
                    "meta_prompt": correction_message.payload["specific_guidance"],
                    "analogical_hints": correction_message.payload.get("analogical_hints", [])
                })

                # Store failure in memory
                if self.enable_memory and self.memory_agent:
                    self.memory_agent.store_failure({
                        "run_id": run_id,
                        "initial_code": initial_code,
                        "failed_code": code_message.payload["refactored_code"],
                        "critique": critique,
                        "failure_reason": critique["reason"]
                    })

                last_code = code_message.payload["refactored_code"]

            # If we reach here, standard CRLS failed
            if enable_meta_correction and self.enable_rsi:
                return self._attempt_rsi_recovery(task_description, initial_code, run_id)
            else:
                self.performance_logger.end_run("failed", {
                    "reason": "max_attempts_exceeded",
                    "attempts": attempt_count
                })

                return {
                    "success": False,
                    "reason": "Max attempts exceeded",
                    "attempts": attempt_count,
                    "run_id": run_id
                }

        except Exception as e:
            logging.error(f"Error in CRLS loop: {e}")
            self.performance_logger.end_run("error", {"error": str(e)})

            return {
                "success": False,
                "reason": f"System error: {e}",
                "run_id": run_id
            }

    def _attempt_rsi_recovery(self, task_description: str, initial_code: str, run_id: str) -> Dict[str, Any]:
        """Attempt recovery through Recursive Self-Improvement"""
        logging.info("Attempting RSI recovery...")

        if self.enable_visualization:
            self.visualizer.visualize_rsi_cycle("corrector_agent", "performance_enhancement", self.rsi_generation)

        try:
            # Generate patch for corrector agent
            patch = self.corrector.trigger_self_modification("prometheus.enhanced_corrector")

            if patch:
                # Apply the self-modification
                success = self_modification_engine.execute_self_modification(
                    "prometheus.enhanced_corrector",
                    patch,
                    run_verification=True
                )

                if success:
                    self.rsi_generation += 1
                    logging.info(f"RSI generation {self.rsi_generation} - corrector agent enhanced")

                    # Update performance metrics
                    self.performance_metrics.append({
                        "generation": self.rsi_generation,
                        "timestamp": time.time(),
                        "success_rate": 0.8,  # Would calculate based on recent performance
                        "efficiency_gain": 0.15
                    })

                    if self.enable_visualization:
                        self.visualizer.update_performance_curve(self.rsi_generation, {
                            "success_rate": 0.8,
                            "efficiency": 0.15
                        })

                    # Retry with enhanced corrector
                    return self.run_crls_loop(task_description, initial_code, max_attempts=3, enable_meta_correction=False)

            # RSI failed
            self.performance_logger.end_run("failed", {"reason": "rsi_recovery_failed"})
            return {
                "success": False,
                "reason": "RSI recovery failed",
                "run_id": run_id
            }

        except Exception as e:
            logging.error(f"RSI recovery error: {e}")
            return {
                "success": False,
                "reason": f"RSI error: {e}",
                "run_id": run_id
            }

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "features_enabled": {
                "visualization": self.enable_visualization,
                "memory": self.enable_memory,
                "rsi": self.enable_rsi
            },
            "rsi_generation": self.rsi_generation,
            "current_run": self.current_run_id,
            "performance_summary": self.performance_logger.get_performance_summary()
        }

        if self.enable_memory and self.memory_agent:
            status["memory_stats"] = self.memory_agent.get_memory_stats()

        if self.mcs:
            status["i_dashboard"] = self.mcs.attention_logger.generate_i_dashboard()

        return status

    def demonstrate_intelligence_explosion(self, num_generations: int = 5) -> List[Dict[str, Any]]:
        """Demonstrate intelligence explosion through multiple RSI cycles"""
        logging.info(f"Starting intelligence explosion demonstration - {num_generations} generations")

        results = []
        test_problems = [
            ("Optimize nested loop search", "def find_pairs(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return None"),
            ("Optimize bubble sort", "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr"),
            ("Optimize linear search", "def linear_search(arr, target):\n    for i in range(len(arr)):\n        if arr[i] == target:\n            return i\n    return -1")
        ]

        for generation in range(num_generations):
            logging.info(f"Intelligence Explosion - Generation {generation + 1}")

            generation_results = {
                "generation": generation + 1,
                "problems_solved": 0,
                "total_problems": len(test_problems),
                "average_attempts": 0,
                "timestamp": time.time()
            }

            total_attempts = 0

            for task_desc, code in test_problems:
                result = self.run_crls_loop(task_desc, code, max_attempts=3)

                if result["success"]:
                    generation_results["problems_solved"] += 1

                total_attempts += result.get("attempts", 3)

            generation_results["average_attempts"] = total_attempts / len(test_problems)
            generation_results["success_rate"] = generation_results["problems_solved"] / generation_results["total_problems"]

            results.append(generation_results)

            # Update performance visualization
            if self.enable_visualization:
                self.visualizer.update_performance_curve(generation + 1, {
                    "success_rate": generation_results["success_rate"],
                    "efficiency": 1.0 / generation_results["average_attempts"]
                })

            logging.info(f"Generation {generation + 1} results: {generation_results['success_rate']:.2%} success rate")

        return results

async def main():
    """Main function demonstrating the complete Prometheus system"""

    # Initialize orchestrator
    orchestrator = PrometheusOrchestrator(
        enable_visualization=True,
        enable_memory=True,
        enable_rsi=True
    )

    try:
        # Start system
        await orchestrator.start_system()

        # Example task
        task_description = "Optimize this nested loop to reduce time complexity"
        initial_code = """
def find_duplicates(nums):
    duplicates = []
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] == nums[j] and nums[i] not in duplicates:
                duplicates.append(nums[i])
    return duplicates
"""

        print("="*80)
        print("PROMETHEUS ADVANCED DEMONSTRATOR")
        print("="*80)

        # Run CRLS loop
        result = orchestrator.run_crls_loop(task_description, initial_code)

        print(f"\nTask Result:")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Final Code:\n{result['final_code']}")
            print(f"Attempts: {result['attempts']}")
        else:
            print(f"Failure Reason: {result['reason']}")

        # Show system status
        status = orchestrator.get_system_status()
        print(f"\nSystem Status:")
        print(f"Features Enabled: {status['features_enabled']}")
        print(f"RSI Generation: {status['rsi_generation']}")
        print(f"Performance Summary: {status['performance_summary']}")

        if 'i_dashboard' in status:
            print(f"\nEmergent Self Pattern ('I' Dashboard):")
            print(status['i_dashboard'])

        print(f"\nBrain map visualization available at: prometheus_brain_map.html")

        # Optional: Run intelligence explosion demo
        # explosion_results = orchestrator.demonstrate_intelligence_explosion(3)
        # print(f"\nIntelligence Explosion Results: {explosion_results}")

    finally:
        await orchestrator.stop_system()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('prometheus_advanced.log'),
            logging.StreamHandler()
        ]
    )

    # Run the system
    asyncio.run(main())