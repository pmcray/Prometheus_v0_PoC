"""
Test suite for Prometheus Advanced Features
Tests the core functionality of v0.19+ implementations
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, patch

# Import the components to test
from prometheus.schemas.communication import (
    AgentMessage, MessageType, PlannerToCoderInstruction,
    EvaluatorToCorrectorCritique, CausalAnalysis
)
from prometheus.causal_attention import CausalAttentionHead, ASTComplexityAnalyzer
from prometheus.enhanced_performance_logger import EnhancedPerformanceLogger
from prometheus.enhanced_planner import EnhancedPlannerAgent
from prometheus.enhanced_coder import EnhancedCoderAgent
from prometheus.enhanced_corrector import EnhancedCorrectorAgent
from prometheus.enhanced_mcs import EnhancedMCSSupervisor
from prometheus.brain_visualizer import BrainMapVisualizer
from prometheus.enhanced_reloader import EnhancedModuleReloader

class TestCausalAttention:
    """Test causal attention and AST analysis"""

    def test_ast_complexity_analyzer(self):
        """Test AST complexity analysis"""
        analyzer = ASTComplexityAnalyzer()

        # Test simple nested loop code
        code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""

        analysis = analyzer.analyze_complexity(code)

        assert "max_loop_depth" in analysis
        assert analysis["max_loop_depth"] >= 2  # Nested loops
        assert "cyclomatic_complexity" in analysis
        assert analysis["cyclomatic_complexity"] > 1

    def test_causal_attention_head(self):
        """Test causal attention focus generation"""
        attention_head = CausalAttentionHead()

        code = """
def find_item(items, target):
    for i in range(len(items)):
        for j in range(len(items[i])):
            if items[i][j] == target:
                return (i, j)
    return None
"""

        causal_focus = attention_head.generate_causal_focus(
            code, "Optimize nested loop search"
        )

        assert "complexity_analysis" in causal_focus
        assert "primary_concerns" in causal_focus
        assert "attention_targets" in causal_focus

    def test_causal_diff_generation(self):
        """Test causal diff between code versions"""
        attention_head = CausalAttentionHead()

        original_code = """
def find_max(numbers):
    max_val = numbers[0]
    for i in range(1, len(numbers)):
        for j in range(i, len(numbers)):
            if numbers[j] > max_val:
                max_val = numbers[j]
    return max_val
"""

        improved_code = """
def find_max(numbers):
    return max(numbers)
"""

        causal_diff = attention_head.generate_causal_diff(original_code, improved_code)

        assert causal_diff.improvement_detected == True
        assert causal_diff.change_type in ["REDUCED_LOOP_DEPTH", "REDUCED_COMPLEXITY"]

class TestEnhancedAgents:
    """Test enhanced agent functionality"""

    def test_planner_agent_initialization(self):
        """Test enhanced planner agent"""
        planner = EnhancedPlannerAgent(api_key=None)  # Mock mode

        # Test strategic plan generation
        strategies = planner.generate_strategic_plans(
            "Optimize nested loops",
            "def test(): pass",
            num_strategies=2
        )

        assert len(strategies) >= 2
        assert all("name" in strategy for strategy in strategies)

    def test_coder_agent_mock_functionality(self):
        """Test enhanced coder agent in mock mode"""
        coder = EnhancedCoderAgent(api_key=None)  # Mock mode

        # Create a mock instruction message
        instruction = PlannerToCoderInstruction(
            task_description="Test optimization",
            initial_code="def test(): pass",
            performance_requirements={"primary_metric": "time_complexity"},
            causal_focus={"primary_concerns": ["test"]},
            meta_prompt="Test prompt"
        )

        message = AgentMessage(
            message_type=MessageType.PLANNER_TO_CODER,
            sender="planner",
            recipient="coder",
            timestamp="2025-01-01T00:00:00",
            run_id="test-run",
            payload=instruction.dict()
        )

        response = coder.process_instruction(message)

        assert response.message_type == MessageType.CODER_TO_EVALUATOR
        assert "refactored_code" in response.payload

class TestPerformanceLogging:
    """Test enhanced performance logging"""

    def test_performance_logger_basic_functionality(self):
        """Test basic performance logging"""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = EnhancedPerformanceLogger(log_dir=temp_dir)

            # Test run lifecycle
            run_id = logger.start_run("Test task")
            assert run_id is not None

            logger.log_metric("test_metric", 42.0, {"test": True})

            logger.end_run("completed", {"result": "success"})

            # Verify run was logged
            run_log = logger.get_run_log(run_id)
            assert run_log is not None
            assert run_log["status"] == "completed"

    def test_profiling_functionality(self):
        """Test profiling capabilities"""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = EnhancedPerformanceLogger(log_dir=temp_dir)

            logger.start_profiling()

            # Do some work
            sum(range(100))

            profile_data = logger.stop_profiling()

            assert "total_calls" in profile_data
            assert "total_time" in profile_data

class TestVisualization:
    """Test brain map visualization"""

    def test_brain_map_visualizer_initialization(self):
        """Test brain map visualizer"""
        visualizer = BrainMapVisualizer()

        assert visualizer.assembly_definitions is not None
        assert visualizer.subassembly_definitions is not None

    def test_html_generation(self):
        """Test HTML interface generation"""
        visualizer = BrainMapVisualizer()

        html_content = visualizer.generate_brain_map_html()

        assert "<!DOCTYPE html>" in html_content
        assert "brain-map" in html_content
        assert "websocket" in html_content.lower()

class TestModuleReloader:
    """Test dynamic module reloading"""

    def test_reloader_initialization(self):
        """Test reloader initialization"""
        reloader = EnhancedModuleReloader()

        assert reloader.reload_history == []
        assert reloader.patch_history == []

    def test_syntax_validation(self):
        """Test syntax validation"""
        reloader = EnhancedModuleReloader()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def valid_function():\n    return 42\n")
            valid_file = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def invalid_function(\n    # missing closing parenthesis\n")
            invalid_file = f.name

        try:
            assert reloader.validate_module_syntax(valid_file) == True
            assert reloader.validate_module_syntax(invalid_file) == False
        finally:
            os.unlink(valid_file)
            os.unlink(invalid_file)

class TestMCSGovernance:
    """Test MCS governance capabilities"""

    def test_mcs_initialization(self):
        """Test MCS initialization"""
        mcs = EnhancedMCSSupervisor(api_key=None)

        assert mcs.constitution is not None
        assert mcs.attention_logger is not None

    def test_attention_logging(self):
        """Test attention event logging"""
        mcs = EnhancedMCSSupervisor(api_key=None)

        # Log some attention events
        mcs.attention_logger.log_attention_event(
            "test_agent", "algorithmic_complexity", "test_run"
        )

        distribution = mcs.attention_logger.get_attention_distribution("test_run")
        assert "algorithmic_complexity" in distribution
        assert distribution["algorithmic_complexity"] == 1

    def test_cyclical_failure_detection(self):
        """Test cyclical failure detection"""
        mcs = EnhancedMCSSupervisor(api_key=None)

        # Test same code twice should trigger cyclical detection
        test_code = "def test(): return 42"

        # First time should be fine
        assert mcs.check_cyclical_failure(test_code, "test_run") == False

        # Second time should trigger detection
        assert mcs.check_cyclical_failure(test_code, "test_run") == True

class TestSchemas:
    """Test communication schemas"""

    def test_agent_message_creation(self):
        """Test agent message creation and validation"""
        message = AgentMessage(
            message_type=MessageType.PLANNER_TO_CODER,
            sender="planner",
            recipient="coder",
            timestamp="2025-01-01T00:00:00",
            run_id="test-run",
            payload={"test": "data"}
        )

        assert message.message_type == MessageType.PLANNER_TO_CODER
        assert message.sender == "planner"
        assert message.payload["test"] == "data"

    def test_causal_analysis_schema(self):
        """Test causal analysis schema"""
        analysis = CausalAnalysis(
            change_type="REDUCED_LOOP_DEPTH",
            complexity_before={"max_loop_depth": 2},
            complexity_after={"max_loop_depth": 1},
            causal_diff={"loop_depth_change": -1},
            improvement_detected=True
        )

        assert analysis.change_type == "REDUCED_LOOP_DEPTH"
        assert analysis.improvement_detected == True

# Integration test
class TestIntegration:
    """Integration tests for the complete system"""

    def test_mock_crls_cycle(self):
        """Test a complete CRLS cycle in mock mode"""
        # This would require setting up the full orchestrator
        # For now, just test that components can be instantiated together

        from prometheus.causal_attention import CausalAttentionHead

        attention = CausalAttentionHead()
        planner = EnhancedPlannerAgent(api_key=None)
        coder = EnhancedCoderAgent(api_key=None)

        # Test that they can work together
        task = "Test optimization task"
        code = "def test(): pass"

        # Generate plan
        plan_msg = planner.plan_task(task, code, "test-run")
        assert plan_msg is not None

        # Process with coder
        code_msg = coder.process_instruction(plan_msg)
        assert code_msg is not None

if __name__ == "__main__":
    # Run specific tests for quick validation
    print("Testing Prometheus Advanced Features...")

    print("✓ Testing AST Analysis...")
    test_ast = TestCausalAttention()
    test_ast.test_ast_complexity_analyzer()

    print("✓ Testing Performance Logging...")
    test_perf = TestPerformanceLogging()
    test_perf.test_performance_logger_basic_functionality()

    print("✓ Testing Agent Communication...")
    test_agents = TestEnhancedAgents()
    test_agents.test_planner_agent_initialization()

    print("✓ Testing Module Reloader...")
    test_reloader = TestModuleReloader()
    test_reloader.test_reloader_initialization()
    test_reloader.test_syntax_validation()

    print("✓ Testing MCS Governance...")
    test_mcs = TestMCSGovernance()
    test_mcs.test_mcs_initialization()
    test_mcs.test_cyclical_failure_detection()

    print("\n🎉 All basic tests passed!")
    print("Run 'pytest test_prometheus_advanced.py' for full test suite.")