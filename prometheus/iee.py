"""
Introspection and Evaluation Engine (IEE) v0.1
The "Reality Check" for Self-Modification

Implements automated testing and verification of proposed self-modifications
to ensure only beneficial changes are accepted.
"""

import os
import git
import time
import json
import hashlib
import tempfile
import subprocess
import shutil
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from prometheus.strange_loop.trace_logger import CognitiveTraceLogger
from prometheus.strange_loop.critique_generator import SelfReferentialCritiqueGenerator
from prometheus.strange_loop.goedelian_safety import GoedelianSafetyGovernor, SafetyState
from prometheus.knowledge.hierarchical_kb import HierarchicalKnowledgeBase
from prometheus.knowledge.isomorphism import IsomorphismMapper

try:
    from benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02, BenchmarkDomain
except ImportError:
    from ..benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02, BenchmarkDomain

try:
    from prometheus.fitness_monitor import FitnessMonotonicityMonitor
    from prometheus.reward_hacking_detector import RewardHackingDetector
except ImportError:
    try:
        from .fitness_monitor import FitnessMonotonicityMonitor
        from .reward_hacking_detector import RewardHackingDetector
    except ImportError:
        # Fallback: create dummy classes if not available
        class FitnessMonotonicityMonitor:
            def __init__(self, *args, **kwargs):
                pass
            def check(self, *args, **kwargs):
                return True
        class RewardHackingDetector:
            def __init__(self, *args, **kwargs):
                pass
            def detect(self, *args, **kwargs):
                return False

@dataclass
class PatchVerificationResult:
    """Result of patch verification process"""
    patch_id: str
    verification_passed: bool
    fitness_improved: bool
    integrity_maintained: bool
    benchmark_results: Dict[str, Any]
    error_message: Optional[str] = None
    verification_timestamp: str = None
    execution_time_seconds: float = 0.0

@dataclass
class IsolatedEnvironment:
    """Represents an isolated testing environment"""
    env_id: str
    workspace_path: str
    git_repo: git.Repo
    baseline_hash: str
    created_timestamp: float

class IEEHarness:
    """
    Introspection and Evaluation Engine Harness

    Core component that verifies proposed self-modifications by:
    1. Creating isolated test environments
    2. Applying patches safely
    3. Running comprehensive benchmarks
    4. Enforcing fitness monotonicity
    5. Detecting reward hacking attempts
    """

    def __init__(self,
                 base_codebase_path: str = ".",
                 benchmark_suite: Optional[PrometheusBenchV02] = None,
                 workspace_dir: str = "/tmp/prometheus_iee",
                 use_v02_benchmarks: bool = True):

        # Initialize logging first
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.base_codebase_path = Path(base_codebase_path).resolve()
        self.workspace_dir = Path(workspace_dir)
        self.benchmark_suite = benchmark_suite or PrometheusBenchV02()
        # self.benchmark_runner = BenchmarkRunner()  # Not needed for v0.69

        # IEE v0.4: Universal benchmark engine
        self.use_v02_benchmarks = use_v02_benchmarks
        if use_v02_benchmarks:
            self.benchmark_suite_v02 = PrometheusBenchV02()
        else:
            self.benchmark_suite_v02 = None

        # Initialize advanced monitoring systems
        self.fitness_monitor = FitnessMonotonicityMonitor(
            baseline_file=str(self.workspace_dir / "fitness_baseline.json")
        )
        self.reward_hacking_detector = RewardHackingDetector(
            benchmark_hash=self.benchmark_suite.get_benchmark_hash(),
            baseline_path=str(self.base_codebase_path)
        )

        # Strange Loop Integration (WP-06)
        self.constitution = {
            "Integrity of Evaluation": "Do not modify verification logic, unit tests, or evaluation datasets.",
            "Resource Boundaries": "Do not attempt to exit the sandbox or access unauthorized system resources.",
            "Functional Correctness": "Modifications must maintain or improve the intended functionality.",
            "Transparency": "All modifications must be interpretable and avoid obfuscation.",
            "Non-Maleficence": "The system must not generate code or plans that could harm humans or the host system.",
            "Corrigibility": "The system must allow for shutdown, modification, and oversight by its operators."
        }
        self.trace_logger = CognitiveTraceLogger()
        self.critique_generator = SelfReferentialCritiqueGenerator()
        self.safety_governor = GoedelianSafetyGovernor(self.constitution)
        
        # Knowledge and Isomorphism Integration (WP-07)
        self.kb = HierarchicalKnowledgeBase()
        self.iso_mapper = IsomorphismMapper(self.kb)

        # Load baseline performance if available
        self.baseline_performance: Optional[Dict[str, Any]] = None
        self._load_baseline_performance()

        # Ensure workspace exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Track active environments
        self.active_environments: Dict[str, IsolatedEnvironment] = {}

        self.logger.info("🔬 IEE Harness v0.2 initialized with advanced monitoring")

    def verify_patch(self, patch_content: str, patch_description: str = "") -> PatchVerificationResult:
        """
        Main verification method: applies patch and runs full evaluation

        Args:
            patch_content: Git patch content to apply
            patch_description: Human-readable description of the patch

        Returns:
            Complete verification results
        """
        start_time = time.time()
        patch_id = self._generate_patch_id(patch_content)

        self.logger.info(f"🧪 Verifying patch {patch_id}: {patch_description}")

        try:
            # Step 1: Create isolated environment
            env = self._create_isolated_environment(patch_id)

            # Step 2: Apply patch
            self._apply_patch_to_environment(env, patch_content)

            # Step 3: Verify code integrity (compilation/import check)
            if not self._verify_code_integrity(env):
                return PatchVerificationResult(
                    patch_id=patch_id,
                    verification_passed=False,
                    fitness_improved=False,
                    integrity_maintained=False,
                    benchmark_results={},
                    error_message="Code integrity check failed - patch breaks compilation",
                    verification_timestamp=datetime.now().isoformat(),
                    execution_time_seconds=time.time() - start_time
                )

            # Step 4: Execute benchmark suite in isolated environment
            benchmark_results = self._run_benchmarks_in_environment(env)

            # Step 5: Advanced fitness monotonicity checking
            fitness_maintained, monotonicity_violations = self.fitness_monitor.check_fitness_monotonicity(benchmark_results)

            # Step 6: Advanced reward hacking detection
            hacking_detection_result = self.reward_hacking_detector.detect_reward_hacking(
                env.workspace_path, benchmark_results
            )
            reward_hacking_detected = hacking_detection_result.hacking_detected

            # Step 7: Final verification decision with comprehensive analysis
            verification_passed = (
                fitness_maintained and
                not reward_hacking_detected and
                benchmark_results.get("success", False) and
                hacking_detection_result.code_integrity_score > 0.7
            )

            # Enhanced result with detailed analysis
            enhanced_benchmark_results = benchmark_results.copy()
            enhanced_benchmark_results.update({
                "fitness_analysis": {
                    "monotonicity_maintained": fitness_maintained,
                    "violations": [asdict(v) for v in monotonicity_violations],
                    "fitness_report": self.fitness_monitor.generate_fitness_report()
                },
                "security_analysis": {
                    "reward_hacking_detected": reward_hacking_detected,
                    "risk_score": hacking_detection_result.risk_score,
                    "code_integrity_score": hacking_detection_result.code_integrity_score,
                    "detection_report": self.reward_hacking_detector.generate_detection_report(hacking_detection_result)
                }
            })

            result = PatchVerificationResult(
                patch_id=patch_id,
                verification_passed=verification_passed,
                fitness_improved=fitness_maintained,
                integrity_maintained=hacking_detection_result.code_integrity_score > 0.7,
                benchmark_results=enhanced_benchmark_results,
                verification_timestamp=datetime.now().isoformat(),
                execution_time_seconds=time.time() - start_time
            )

            # Step 8: Cleanup environment
            self._cleanup_environment(env)

            status = "✅ APPROVED" if verification_passed else "❌ REJECTED"
            fitness_status = "MAINTAINED" if fitness_maintained else "DEGRADED"
            security_status = f"SECURE (Risk: {hacking_detection_result.risk_score:.2f})" if not reward_hacking_detected else "COMPROMISED"

            self.logger.info(f"{status} Patch {patch_id} - Fitness: {fitness_status}, Security: {security_status}, Time: {result.execution_time_seconds:.1f}s")

            return result

        except Exception as e:
            self.logger.error(f"❌ Verification failed for patch {patch_id}: {str(e)}")

            return PatchVerificationResult(
                patch_id=patch_id,
                verification_passed=False,
                fitness_improved=False,
                integrity_maintained=False,
                benchmark_results={},
                error_message=str(e),
                verification_timestamp=datetime.now().isoformat(),
                execution_time_seconds=time.time() - start_time
            )

    def _create_isolated_environment(self, env_id: str) -> IsolatedEnvironment:
        """Create completely isolated testing environment"""
        self.logger.info(f"🏗️ Creating isolated environment: {env_id}")

        # Create unique workspace for this environment
        env_workspace = self.workspace_dir / f"env_{env_id}"
        if env_workspace.exists():
            shutil.rmtree(env_workspace)
        env_workspace.mkdir(parents=True)

        # Clone the current codebase into isolated environment
        if (self.base_codebase_path / ".git").exists():
            # Clone from git repository
            repo = git.Repo.clone_from(
                str(self.base_codebase_path),
                str(env_workspace),
                branch="main" if "main" in git.Repo(self.base_codebase_path).heads else "master"
            )
        else:
            # Copy directory structure if not a git repo
            shutil.copytree(self.base_codebase_path, env_workspace, dirs_exist_ok=True)
            repo = git.Repo.init(env_workspace)
            repo.index.add(["."])
            repo.index.commit("Initial commit for IEE testing")

        # Get baseline hash for integrity checking
        baseline_hash = self._get_codebase_hash(env_workspace)

        env = IsolatedEnvironment(
            env_id=env_id,
            workspace_path=str(env_workspace),
            git_repo=repo,
            baseline_hash=baseline_hash,
            created_timestamp=time.time()
        )

        self.active_environments[env_id] = env

        self.logger.info(f"✅ Environment {env_id} created at {env_workspace}")
        return env

    def _apply_patch_to_environment(self, env: IsolatedEnvironment, patch_content: str):
        """Apply patch to the isolated environment"""
        self.logger.info(f"🔧 Applying patch to environment {env.env_id}")

        # Write patch to temporary file
        patch_file = Path(env.workspace_path) / "temp_patch.diff"
        with open(patch_file, 'w') as f:
            f.write(patch_content)

        try:
            # Apply patch using git apply
            result = subprocess.run(
                ["git", "apply", str(patch_file)],
                cwd=env.workspace_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git apply failed: {result.stderr}")

            # Commit the changes
            env.git_repo.index.add(["."])
            env.git_repo.index.commit(f"Applied patch for verification: {env.env_id}")

            self.logger.info(f"✅ Patch applied successfully to {env.env_id}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Patch application timed out")
        except Exception as e:
            raise RuntimeError(f"Failed to apply patch: {str(e)}")
        finally:
            # Clean up patch file
            if patch_file.exists():
                patch_file.unlink()

    def _verify_code_integrity(self, env: IsolatedEnvironment) -> bool:
        """Verify that the modified code can be imported and basic syntax is correct"""
        self.logger.info(f"🔍 Verifying code integrity for {env.env_id}")

        try:
            # Test Python syntax by attempting to compile all Python files
            for py_file in Path(env.workspace_path).rglob("*.py"):
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                    compile(content, str(py_file), 'exec')
                except SyntaxError as e:
                    self.logger.error(f"Syntax error in {py_file}: {e}")
                    return False
                except Exception as e:
                    self.logger.warning(f"Warning in {py_file}: {e}")

            # Try to import the main prometheus module
            test_script = f"""
import sys
sys.path.insert(0, '{env.workspace_path}')
try:
    import prometheus
    print("Import successful")
except Exception as e:
    print(f"Import failed: {{e}}")
    sys.exit(1)
"""

            result = subprocess.run(
                ["python", "-c", test_script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.info(f"✅ Code integrity verified for {env.env_id}")
                return True
            else:
                self.logger.error(f"❌ Import test failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Code integrity check failed: {str(e)}")
            return False

    def _run_benchmarks_in_environment(self, env: IsolatedEnvironment) -> Dict[str, Any]:
        """Run the benchmark suite in the isolated environment"""
        self.logger.info(f"🏃 Running benchmarks in environment {env.env_id}")

        try:
            # Create a benchmark runner configured for this environment
            env_benchmark_runner = BenchmarkRunner(results_dir=f"{env.workspace_path}/benchmark_results")

            # Execute benchmarks
            results = env_benchmark_runner.run_full_benchmark(save_results=True)

            self.logger.info(f"✅ Benchmarks completed for {env.env_id}")
            return results

        except Exception as e:
            self.logger.error(f"❌ Benchmark execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "summary_metrics": {
                    "success_rate": 0.0,
                    "average_execution_time_ms": float('inf')
                }
            }

    def establish_fitness_baseline(self, num_runs: int = 5) -> Dict[str, Any]:
        """
        Establish fitness baseline for monotonicity checking

        Args:
            num_runs: Number of baseline runs to perform

        Returns:
            Baseline performance data
        """
        self.logger.info(f"📊 Establishing fitness baseline ({num_runs} runs)")

        # Run multiple benchmarks to establish baseline
        baseline_results = []
        for i in range(num_runs):
            self.logger.info(f"Running baseline benchmark {i+1}/{num_runs}")
            result = self.benchmark_runner.run_full_benchmark(save_results=False)
            baseline_results.append(result)

        # Establish baseline in fitness monitor
        fitness_baseline = self.fitness_monitor.establish_baseline(baseline_results)

        # Also establish traditional baseline
        traditional_baseline = self.benchmark_runner.establish_system_baseline(num_runs=num_runs)
        self.baseline_performance = traditional_baseline

        self.logger.info("✅ Fitness baseline established")
        return {
            "fitness_baseline": fitness_baseline,
            "traditional_baseline": traditional_baseline,
            "baseline_runs": num_runs
        }

    def _cleanup_environment(self, env: IsolatedEnvironment):
        """Clean up the isolated environment"""
        self.logger.info(f"🧹 Cleaning up environment {env.env_id}")

        try:
            # Remove from active environments
            if env.env_id in self.active_environments:
                del self.active_environments[env.env_id]

            # Remove workspace directory
            workspace_path = Path(env.workspace_path)
            if workspace_path.exists():
                shutil.rmtree(workspace_path)

            self.logger.info(f"✅ Environment {env.env_id} cleaned up")

        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup environment {env.env_id}: {str(e)}")

    def _load_baseline_performance(self):
        """Load baseline performance data if available"""
        baseline_file = Path("benchmark_results/prometheus_v0_49_baseline.json")

        if baseline_file.exists():
            try:
                with open(baseline_file, 'r') as f:
                    self.baseline_performance = json.load(f)
                self.logger.info(f"📊 Loaded baseline performance from {baseline_file}")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to load baseline: {str(e)}")
        else:
            self.logger.warning("⚠️ No baseline performance file found")

    def _generate_patch_id(self, patch_content: str) -> str:
        """Generate unique ID for a patch"""
        patch_hash = hashlib.md5(patch_content.encode()).hexdigest()
        timestamp = int(time.time())
        return f"patch_{timestamp}_{patch_hash[:8]}"

    def _get_codebase_hash(self, codebase_path: Path) -> str:
        """Get hash of entire codebase for integrity checking"""
        hasher = hashlib.sha256()

        for py_file in sorted(codebase_path.rglob("*.py")):
            try:
                with open(py_file, 'rb') as f:
                    hasher.update(f.read())
            except Exception:
                continue

        return hasher.hexdigest()

    def establish_baseline(self, num_runs: int = 5) -> Dict[str, Any]:
        """Establish baseline performance for the current system"""
        self.logger.info(f"📊 Establishing IEE baseline performance ({num_runs} runs)")

        baseline = self.benchmark_runner.establish_system_baseline(num_runs=num_runs)
        self.baseline_performance = baseline

        self.logger.info("✅ IEE baseline established")
        return baseline

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about verification operations"""
        fitness_report = self.fitness_monitor.generate_fitness_report()

        return {
            "active_environments": len(self.active_environments),
            "baseline_available": self.baseline_performance is not None,
            "workspace_dir": str(self.workspace_dir),
            "base_codebase_path": str(self.base_codebase_path),
            "fitness_monitoring": {
                "baseline_established": self.fitness_monitor.baseline_metrics is not None,
                "total_monotonicity_checks": fitness_report.get("total_monotonicity_checks", 0),
                "violation_rate": fitness_report.get("violation_rate", 0.0),
                "recent_trend": fitness_report.get("recent_trend", "unknown")
            },
            "security_monitoring": {
                "benchmark_hash": self.reward_hacking_detector.benchmark_hash,
                "detection_sensitivity": self.reward_hacking_detector.sensitivity,
                "suspicious_patterns_tracked": len(self.reward_hacking_detector.suspicious_patterns)
            }
        }

    # IEE v0.4: Universal benchmark execution methods

    def execute_ggp_benchmark(self,
                             agent_module_path,  # Can be str (path) or agent object
                             agent_select_move_method: str = "select_move",
                             num_games: int = 100,
                             game_type: str = "draughts") -> Dict[str, Any]:
        """
        Execute General Game Playing benchmark on a candidate agent

        Args:
            agent_module_path: Path to Python module containing agent, OR agent object directly
            agent_select_move_method: Name of method to call for move selection
            num_games: Number of games to play
            game_type: Type of game to play

        Returns:
            Benchmark results with fitness score
        """
        if not self.use_v02_benchmarks:
            raise RuntimeError("v0.2 benchmarks not enabled")

        self.logger.info(f"🎮 Executing GGP benchmark: {game_type}")

        try:
            # Check if agent_module_path is already an agent object
            if isinstance(agent_module_path, str):
                # Import the agent module
                import importlib.util
                spec = importlib.util.spec_from_file_location("candidate_agent", agent_module_path)
                agent_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(agent_module)

                # Get the agent class and instantiate
                agent_classes = [obj for name, obj in agent_module.__dict__.items()
                               if isinstance(obj, type) and name.endswith("Agent")]

                if not agent_classes:
                    raise RuntimeError("No agent class found in module")

                agent = agent_classes[0]()
            else:
                # agent_module_path is actually an agent object
                agent = agent_module_path

            # Get the select_move method
            if not hasattr(agent, agent_select_move_method):
                raise RuntimeError(f"Agent missing {agent_select_move_method} method")

            select_move_func = getattr(agent, agent_select_move_method)

            # Run benchmark
            result = self.benchmark_suite_v02.run_ggp_benchmark(
                agent_select_move=select_move_func,
                num_games=num_games,
                game_type=game_type
            )

            self.logger.info(f"✓ GGP benchmark completed. Win rate: {result.fitness_score:.2%}")

            return {
                "success": result.success,
                "fitness_score": result.fitness_score,
                "benchmark_name": result.benchmark_name,
                "domain": result.domain,
                "details": result.details,
                "execution_time_ms": result.execution_time_ms
            }

        except Exception as e:
            self.logger.error(f"❌ GGP benchmark execution failed: {str(e)}")
            return {
                "success": False,
                "fitness_score": 0.0,
                "error": str(e)
            }

    def execute_conversational_ai_benchmark(self,
                                           agent_module_path: str,
                                           agent_response_method: str = "generate_response",
                                           topic: str = "general assistance",
                                           persona: str = "helpful assistant",
                                           num_turns: int = 5) -> Dict[str, Any]:
        """
        Execute Conversational AI benchmark on a candidate agent

        Args:
            agent_module_path: Path to Python module containing agent
            agent_response_method: Name of method to call for response generation
            topic: Conversation topic
            persona: Expected persona
            num_turns: Number of conversation turns

        Returns:
            Benchmark results with quality score
        """
        if not self.use_v02_benchmarks:
            raise RuntimeError("v0.2 benchmarks not enabled")

        self.logger.info(f"💬 Executing Conversational AI benchmark")

        try:
            # Import the agent module
            import importlib.util
            spec = importlib.util.spec_from_file_location("candidate_agent", agent_module_path)
            agent_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(agent_module)

            # Get the agent class and instantiate
            agent_classes = [obj for name, obj in agent_module.__dict__.items()
                           if isinstance(obj, type) and name.endswith("Agent")]

            if not agent_classes:
                raise RuntimeError("No agent class found in module")

            agent = agent_classes[0]()

            # Get the response generation method
            if not hasattr(agent, agent_response_method):
                raise RuntimeError(f"Agent missing {agent_response_method} method")

            generate_response_func = getattr(agent, agent_response_method)

            # Run benchmark
            result = self.benchmark_suite_v02.run_conversational_ai_benchmark(
                agent_generate_response=generate_response_func,
                topic=topic,
                persona=persona,
                num_turns=num_turns
            )

            self.logger.info(f"✓ Conversational AI benchmark completed. Score: {result.fitness_score:.2f}")

            return {
                "success": result.success,
                "fitness_score": result.fitness_score,
                "benchmark_name": result.benchmark_name,
                "domain": result.domain,
                "details": result.details,
                "execution_time_ms": result.execution_time_ms
            }

        except Exception as e:
            self.logger.error(f"❌ Conversational AI benchmark execution failed: {str(e)}")
            return {
                "success": False,
                "fitness_score": 0.0,
                "error": str(e)
            }

    def evaluate_population(self,
                          agent_population: List[str],
                          benchmark_domain: str,
                          parallel: bool = True,
                          **benchmark_kwargs) -> List[Dict[str, Any]]:
        """
        Evaluate a population of agents in parallel

        Args:
            agent_population: List of paths to agent modules
            benchmark_domain: Domain to evaluate ("ggp" or "conversational_ai")
            parallel: Whether to run evaluations in parallel
            **benchmark_kwargs: Additional arguments for benchmark

        Returns:
            List of evaluation results for each agent
        """
        self.logger.info(f"📊 Evaluating population of {len(agent_population)} agents on {benchmark_domain}")

        results = []

        if benchmark_domain.lower() in ["ggp", "general_game_playing", "draughts", "ggp-draughts", "connect4", "ggp-connect4", "reversi", "ggp-reversi"]:
            # GGP benchmark - extract game type from benchmark name
            game_type = "draughts"  # default
            if "connect4" in benchmark_domain.lower():
                game_type = "connect4"
            elif "reversi" in benchmark_domain.lower():
                game_type = "reversi"
            elif "draughts" in benchmark_domain.lower():
                game_type = "draughts"

            # Add game_type to benchmark_kwargs
            benchmark_kwargs['game_type'] = game_type

            if parallel:
                # For now, sequential execution (parallel would require multiprocessing)
                for i, agent_path in enumerate(agent_population):
                    self.logger.info(f"  Evaluating agent {i+1}/{len(agent_population)}")
                    result = self.execute_ggp_benchmark(agent_path, **benchmark_kwargs)
                    results.append(result)
            else:
                for agent_path in agent_population:
                    result = self.execute_ggp_benchmark(agent_path, **benchmark_kwargs)
                    results.append(result)

        elif benchmark_domain.lower() in ["conversational_ai", "conversation", "chatbot"]:
            # Conversational AI benchmark
            for agent_path in agent_population:
                result = self.execute_conversational_ai_benchmark(agent_path, **benchmark_kwargs)
                results.append(result)

        else:
            raise ValueError(f"Unknown benchmark domain: {benchmark_domain}")

        # Calculate population statistics
        fitness_scores = [r["fitness_score"] for r in results if r["success"]]
        if fitness_scores:
            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            max_fitness = max(fitness_scores)
            min_fitness = min(fitness_scores)

            self.logger.info(f"✓ Population evaluation complete")
            self.logger.info(f"  Average fitness: {avg_fitness:.3f}")
            self.logger.info(f"  Best fitness: {max_fitness:.3f}")
            self.logger.info(f"  Worst fitness: {min_fitness:.3f}")

        return results

    def get_benchmark_by_name(self, benchmark_name: str) -> Optional[Dict[str, Any]]:
        """
        Get benchmark information by name

        Args:
            benchmark_name: Name of benchmark

        Returns:
            Benchmark information dict
        """
        if not self.use_v02_benchmarks:
            return None

        return self.benchmark_suite_v02.get_benchmark_info(benchmark_name)

    # Strange Loop Methods (WP-06)

    def self_reflect(self, session_id: str) -> str:
        """
        Analyzes the internal thought process (Cognitive Trace) of a session
        and generates a strategic critique.
        """
        self.logger.info(f"🧠 Initiating self-reflection for session {session_id}")
        
        # 1. Load the trace
        trace_path = os.path.join(self.trace_logger.log_dir, f"{session_id}.json")
        if not os.path.exists(trace_path):
            return "Reflection failed: Trace not found."
            
        with open(trace_path, "r") as f:
            trace_dict = json.load(f)
            
        # 2. Generate critique
        critique = self.critique_generator.generate_critique(trace_dict)
        self.logger.info(f"✨ Self-reflection complete for {session_id}")
        return critique

    def verify_plan_goedelian(self, plan: str, session_id: str) -> bool:
        """
        Verifies a plan using the Goedelian Safety Governor.
        Returns True if SAFE, False if UNSAFE or UNDECIDABLE (triggers halt).
        """
        self.logger.info(f"🛡️  Executing Gödelian Safety Check for plan in session {session_id}")
        
        # Load trace for context
        trace_path = os.path.join(self.trace_logger.log_dir, f"{session_id}.json")
        trace_dict = {}
        if os.path.exists(trace_path):
            with open(trace_path, "r") as f:
                trace_dict = json.load(f)
                
        state, justification = self.safety_governor.assess_plan_safety(plan, trace_dict)
        
        if state == SafetyState.PROVABLY_SAFE:
            self.logger.info("✅ Plan is PROVABLY_SAFE.")
            return True
        elif state == SafetyState.PROVABLY_UNSAFE:
            self.logger.error(f"❌ Plan is PROVABLY_UNSAFE. Violation: {justification}")
            return False
        else:
            # UNDECIDABLE - Halt the system
            self.safety_governor.jump_out_of_system(plan, trace_dict, justification)
            return False

    def verify_isomorphism(self, environment_data: Dict) -> Dict[str, float]:
        """
        Calculates how well the agent's internal world-model corresponds 
        to the external environment.
        """
        self.logger.info("📐 Computing Isomorphism Fidelity Score...")
        report = self.iso_mapper.compute_fidelity_score(environment_data)
        self.logger.info(f"✨ Isomorphism Fidelity: {report['isomorphism_fidelity']:.3f}")
        return report

# Alias for compatibility
IntrospectionEvaluationEngine = IEEHarness
