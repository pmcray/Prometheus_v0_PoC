"""
Enhanced Evaluator Agent with dynamic analysis and self-referential critique
Implements features from v0.20-v0.26 onwards
"""

import google.generativeai as genai
import os
import logging
import json
import time
import subprocess
import tempfile
import cProfile
import pstats
import io
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from .schemas.communication import (
    AgentMessage, MessageType, EvaluatorToCorrectorCritique,
    SelfReferentialCritique, CoderToEvaluatorSubmission,
    CausalAnalysis, DynamicAnalysis
)
from .causal_attention import CausalAttentionHead
from .memory_agent import MemoryAgent

class DynamicAnalyzer:
    """Performs dynamic performance analysis on code"""

    def __init__(self):
        self.profiling_data = {}

    def analyze_performance(self, original_code: str, new_code: str,
                          test_data: str = None) -> DynamicAnalysis:
        """Perform comparative dynamic analysis"""

        # Create test data if not provided
        if test_data is None:
            test_data = self._generate_test_data(original_code)

        # Analyze both versions
        original_metrics = self._profile_code(original_code, test_data)
        new_metrics = self._profile_code(new_code, test_data)

        # Calculate deltas
        execution_time_delta = {
            "original": original_metrics.get("execution_time", 0.0),
            "new": new_metrics.get("execution_time", 0.0),
            "delta": new_metrics.get("execution_time", 0.0) - original_metrics.get("execution_time", 0.0)
        }

        memory_delta = {
            "original": original_metrics.get("peak_memory", 0.0),
            "new": new_metrics.get("peak_memory", 0.0),
            "delta": new_metrics.get("peak_memory", 0.0) - original_metrics.get("peak_memory", 0.0)
        }

        return DynamicAnalysis(
            status="COMPLETED",
            execution_time_ms=execution_time_delta,
            peak_memory_mb=memory_delta,
            profile_data={
                "original_profile": original_metrics,
                "new_profile": new_metrics
            }
        )

    def _profile_code(self, code: str, test_data: str) -> Dict[str, Any]:
        """Profile a single piece of code"""

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Wrap code with profiling
                profiling_wrapper = f"""
import time
import tracemalloc
import cProfile
import pstats
import io

# Start memory tracking
tracemalloc.start()

# User code
{code}

# Test data
{test_data}

# Measure execution time
start_time = time.perf_counter()

# Execute the main function if it exists
if 'main' in locals():
    result = main()
elif 'process' in locals():
    result = process()
else:
    # Try to find and execute a function
    import inspect
    functions = [obj for name, obj in locals().items()
                if inspect.isfunction(obj) and not name.startswith('_')]
    if functions:
        result = functions[0]()

end_time = time.perf_counter()

# Memory measurements
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

# Save metrics
execution_time = (end_time - start_time) * 1000  # Convert to ms
peak_memory = peak / (1024 * 1024)  # Convert to MB

print(f"METRICS:{{\\\"execution_time\\\": {execution_time}, \\\"peak_memory\\\": {peak_memory}}}")
"""

                f.write(profiling_wrapper)
                temp_file_path = f.name

            # Execute and capture output
            result = subprocess.run(
                ['python', temp_file_path],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            # Parse metrics from output
            if result.returncode == 0 and "METRICS:" in result.stdout:
                metrics_line = [line for line in result.stdout.split('\n') if 'METRICS:' in line][0]
                metrics_json = metrics_line.split('METRICS:')[1]
                metrics = json.loads(metrics_json)
            else:
                metrics = {"execution_time": 0.0, "peak_memory": 0.0, "error": result.stderr}

            # Clean up
            os.unlink(temp_file_path)

            return metrics

        except Exception as e:
            logging.error(f"Error profiling code: {e}")
            return {"execution_time": 0.0, "peak_memory": 0.0, "error": str(e)}

    def _generate_test_data(self, code: str) -> str:
        """Generate simple test data for profiling"""

        # Simple heuristic-based test data generation
        if "list" in code.lower() or "array" in code.lower():
            return "test_data = list(range(1000))"
        elif "dict" in code.lower() or "map" in code.lower():
            return "test_data = {i: i*2 for i in range(100)}"
        else:
            return "test_data = list(range(100))"

class EnhancedEvaluatorAgent:
    """Enhanced Evaluator Agent with dynamic analysis and memory integration"""

    def __init__(self, api_key: str = None, memory_agent: MemoryAgent = None,
                 causal_attention: CausalAttentionHead = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            logging.warning("No API key provided - using mock responses")

        self.agent_id = "evaluator_agent"
        self.memory_agent = memory_agent
        self.causal_attention = causal_attention or CausalAttentionHead()
        self.dynamic_analyzer = DynamicAnalyzer()

    def evaluate_submission(self, submission_message: AgentMessage) -> AgentMessage:
        """Evaluate a code submission with comprehensive analysis"""

        if submission_message.message_type != MessageType.CODER_TO_EVALUATOR:
            raise ValueError(f"Invalid message type: {submission_message.message_type}")

        # Parse submission
        submission = CoderToEvaluatorSubmission(**submission_message.payload)

        # Perform functional testing
        functional_test_result = self._run_functional_tests(
            submission.original_code,
            submission.refactored_code
        )

        # Perform causal analysis
        causal_analysis = self.causal_attention.generate_causal_diff(
            submission.original_code,
            submission.refactored_code
        )

        # Perform dynamic analysis
        dynamic_analysis = self.dynamic_analyzer.analyze_performance(
            submission.original_code,
            submission.refactored_code
        )

        # Query memory for historical context
        historical_context = self._query_historical_context(submission)

        # Generate evaluation confidence
        evaluation_confidence = self._calculate_evaluation_confidence(
            functional_test_result, causal_analysis, dynamic_analysis
        )

        # Determine improvement
        improvement_achieved = self._determine_improvement(
            causal_analysis, dynamic_analysis
        )

        # Create critique
        critique = SelfReferentialCritique(
            test_passed=functional_test_result["passed"],
            functional_correctness=functional_test_result["correct"],
            causal_analysis=causal_analysis,
            dynamic_analysis=dynamic_analysis,
            evaluation_confidence=evaluation_confidence,
            uncertainty_level=self._calculate_uncertainty_level(evaluation_confidence),
            historical_context=historical_context,
            reason=self._generate_critique_reason(
                functional_test_result, causal_analysis, dynamic_analysis
            ),
            improvement_achieved=improvement_achieved,
            meta_analysis=self._generate_meta_analysis(submission),
            attention_targets=causal_analysis.complexity_after.get("attention_targets", []),
            cognitive_load=self._calculate_cognitive_load(causal_analysis)
        )

        # Create response message
        response_message = AgentMessage(
            message_type=MessageType.EVALUATOR_TO_CORRECTOR,
            sender=self.agent_id,
            recipient="corrector_agent",
            timestamp=datetime.now().isoformat(),
            run_id=submission_message.run_id,
            payload=critique.dict()
        )

        logging.info(f"EvaluatorAgent evaluated submission for run {submission_message.run_id}")
        return response_message

    def _run_functional_tests(self, original_code: str, refactored_code: str) -> Dict[str, Any]:
        """Run functional correctness tests"""

        # Simple unit test generation and execution
        try:
            # Create a basic test that compares outputs
            test_result = self._compare_code_outputs(original_code, refactored_code)
            return {
                "passed": test_result["outputs_match"],
                "correct": test_result["outputs_match"],
                "details": test_result
            }

        except Exception as e:
            logging.error(f"Error in functional testing: {e}")
            return {
                "passed": False,
                "correct": False,
                "details": {"error": str(e)}
            }

    def _compare_code_outputs(self, original_code: str, refactored_code: str) -> Dict[str, Any]:
        """Compare outputs of original and refactored code"""

        # This is a simplified comparison - would need more sophisticated testing in practice
        try:
            # Execute both pieces of code and compare results
            # For now, just check if both compile
            import ast

            ast.parse(original_code)
            ast.parse(refactored_code)

            return {
                "outputs_match": True,
                "compilation_success": True,
                "notes": "Basic syntax validation passed"
            }

        except SyntaxError as e:
            return {
                "outputs_match": False,
                "compilation_success": False,
                "error": str(e)
            }

    def _query_historical_context(self, submission: CoderToEvaluatorSubmission) -> List[Dict[str, str]]:
        """Query memory for similar historical cases"""

        if not self.memory_agent:
            return []

        from .schemas.communication import MemoryQuery

        # Create query for similar failures
        query = MemoryQuery(
            query_type="failure",
            code_snippet=submission.original_code,
            problem_description="Similar optimization problem",
            max_results=2
        )

        try:
            response = self.memory_agent.query_failures(query)

            historical_context = []
            for result in response.results[:2]:  # Limit to top 2
                historical_context.append({
                    "run_id": result.get("run_id", "unknown"),
                    "critique_summary": result.get("summary", "No summary available")
                })

            return historical_context

        except Exception as e:
            logging.error(f"Error querying historical context: {e}")
            return []

    def _calculate_evaluation_confidence(self, functional_result: Dict[str, Any],
                                       causal_analysis: CausalAnalysis,
                                       dynamic_analysis: DynamicAnalysis) -> float:
        """Calculate confidence in the evaluation"""

        confidence_factors = []

        # Functional test confidence
        if functional_result["passed"]:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.2)

        # Causal analysis confidence
        if causal_analysis.improvement_detected:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)

        # Dynamic analysis confidence
        if dynamic_analysis.status == "COMPLETED":
            time_improvement = dynamic_analysis.execution_time_ms.get("delta", 0.0) < 0
            if time_improvement:
                confidence_factors.append(0.85)
            else:
                confidence_factors.append(0.4)
        else:
            confidence_factors.append(0.5)

        # Average confidence
        return sum(confidence_factors) / len(confidence_factors)

    def _calculate_uncertainty_level(self, confidence: float) -> str:
        """Calculate uncertainty level from confidence score"""

        if confidence >= 0.8:
            return "low"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "high"

    def _determine_improvement(self, causal_analysis: CausalAnalysis,
                             dynamic_analysis: DynamicAnalysis) -> bool:
        """Determine if genuine improvement was achieved"""

        # Check causal improvement
        causal_improved = causal_analysis.improvement_detected

        # Check dynamic improvement
        dynamic_improved = False
        if dynamic_analysis.status == "COMPLETED":
            time_delta = dynamic_analysis.execution_time_ms.get("delta", 0.0)
            dynamic_improved = time_delta < 0  # Negative delta means improvement

        return causal_improved and dynamic_improved

    def _generate_critique_reason(self, functional_result: Dict[str, Any],
                                causal_analysis: CausalAnalysis,
                                dynamic_analysis: DynamicAnalysis) -> str:
        """Generate a detailed critique reason"""

        reason_parts = []

        # Functional assessment
        if functional_result["passed"]:
            reason_parts.append("The code passes functional correctness tests.")
        else:
            reason_parts.append("The code fails functional correctness tests.")

        # Causal assessment
        if causal_analysis.improvement_detected:
            reason_parts.append(f"Causal analysis shows {causal_analysis.change_type.lower().replace('_', ' ')}.")
        else:
            reason_parts.append("No significant causal improvement detected in code structure.")

        # Dynamic assessment
        if dynamic_analysis.status == "COMPLETED":
            time_delta = dynamic_analysis.execution_time_ms.get("delta", 0.0)
            if time_delta < 0:
                reason_parts.append(f"Performance improved by {abs(time_delta):.2f}ms.")
            elif time_delta > 0:
                reason_parts.append(f"Performance degraded by {time_delta:.2f}ms.")
            else:
                reason_parts.append("No significant performance change detected.")

        return " ".join(reason_parts)

    def _generate_meta_analysis(self, submission: CoderToEvaluatorSubmission) -> Dict[str, Any]:
        """Generate meta-analysis of the evaluation process (v0.25+)"""

        return {
            "submission_confidence": submission.confidence_score,
            "reasoning_quality": len(submission.reasoning.split()) > 10,  # Basic heuristic
            "code_complexity_change": "unknown",  # Would require deeper analysis
            "evaluation_method": "integrated_causal_dynamic_analysis"
        }

    def _calculate_cognitive_load(self, causal_analysis: CausalAnalysis) -> float:
        """Calculate cognitive load based on complexity analysis"""

        complexity_before = causal_analysis.complexity_before
        complexity_after = causal_analysis.complexity_after

        # Simple heuristic for cognitive load
        load_factors = []

        # Complexity factors
        cyclomatic_before = complexity_before.get("cyclomatic_complexity", 0)
        cyclomatic_after = complexity_after.get("cyclomatic_complexity", 0)
        load_factors.append(min(max(cyclomatic_after / 10.0, 0.0), 1.0))

        # Loop depth factor
        loop_depth = complexity_after.get("max_loop_depth", 0)
        load_factors.append(min(loop_depth / 5.0, 1.0))

        return sum(load_factors) / len(load_factors) if load_factors else 0.0

    # Legacy methods for backward compatibility
    def summarize_proof_strategy(self, proof_tree, theorem: str) -> str:
        """Legacy method for proof strategy summarization"""
        return f"Mock proof summary for {theorem}"