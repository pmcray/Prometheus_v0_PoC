"""
Simple test for Prometheus Advanced Features
Tests core functionality without complex dependencies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_causal_attention():
    """Test causal attention system"""
    print("Testing Causal Attention...")

    try:
        from prometheus.causal_attention import CausalAttentionHead, ASTComplexityAnalyzer

        # Test AST analysis
        analyzer = ASTComplexityAnalyzer()
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
        assert analysis["max_loop_depth"] >= 2

        print("✅ AST Analysis working")

        # Test causal attention
        attention = CausalAttentionHead()
        focus = attention.generate_causal_focus(code, "Optimize nested loops")
        assert "complexity_analysis" in focus

        print("✅ Causal Attention working")
        return True

    except Exception as e:
        print(f"❌ Causal Attention failed: {e}")
        return False

def test_schemas():
    """Test communication schemas"""
    print("Testing Communication Schemas...")

    try:
        from prometheus.schemas.communication import AgentMessage, MessageType, CausalAnalysis

        # Test basic schema
        analysis = CausalAnalysis(
            change_type="REDUCED_LOOP_DEPTH",
            complexity_before={"max_loop_depth": 2},
            complexity_after={"max_loop_depth": 1},
            causal_diff={"loop_depth_change": -1},
            improvement_detected=True
        )

        assert analysis.change_type == "REDUCED_LOOP_DEPTH"
        assert analysis.improvement_detected == True

        print("✅ Communication Schemas working")
        return True

    except Exception as e:
        print(f"❌ Schemas failed: {e}")
        return False

def test_performance_logger():
    """Test performance logging"""
    print("Testing Performance Logger...")

    try:
        import tempfile
        from prometheus.enhanced_performance_logger import EnhancedPerformanceLogger

        with tempfile.TemporaryDirectory() as temp_dir:
            logger = EnhancedPerformanceLogger(log_dir=temp_dir)

            run_id = logger.start_run("Test task")
            logger.log_metric("test_metric", 42.0)
            logger.end_run("completed")

            run_log = logger.get_run_log(run_id)
            assert run_log["status"] == "completed"

        print("✅ Performance Logger working")
        return True

    except Exception as e:
        print(f"❌ Performance Logger failed: {e}")
        return False

def test_enhanced_agents():
    """Test enhanced agents in mock mode"""
    print("Testing Enhanced Agents...")

    try:
        from prometheus.enhanced_planner import EnhancedPlannerAgent
        from prometheus.enhanced_coder import EnhancedCoderAgent

        # Test planner (mock mode)
        planner = EnhancedPlannerAgent(api_key=None)
        strategies = planner.generate_strategic_plans("Test", "def test(): pass", 2)
        assert len(strategies) >= 2

        # Test coder (mock mode)
        coder = EnhancedCoderAgent(api_key=None)
        assert coder.agent_id == "coder_agent"

        print("✅ Enhanced Agents working")
        return True

    except Exception as e:
        print(f"❌ Enhanced Agents failed: {e}")
        return False

def test_brain_visualizer():
    """Test brain visualization"""
    print("Testing Brain Visualizer...")

    try:
        from prometheus.brain_visualizer import BrainMapVisualizer

        visualizer = BrainMapVisualizer()
        html = visualizer.generate_brain_map_html()

        assert "<!DOCTYPE html>" in html
        assert "brain-map" in html

        print("✅ Brain Visualizer working")
        return True

    except Exception as e:
        print(f"❌ Brain Visualizer failed: {e}")
        return False

def test_reloader():
    """Test module reloader"""
    print("Testing Module Reloader...")

    try:
        from prometheus.enhanced_reloader import EnhancedModuleReloader
        import tempfile

        reloader = EnhancedModuleReloader()

        # Test syntax validation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test():\n    return 42\n")
            valid_file = f.name

        assert reloader.validate_module_syntax(valid_file) == True

        os.unlink(valid_file)

        print("✅ Module Reloader working")
        return True

    except Exception as e:
        print(f"❌ Module Reloader failed: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("PROMETHEUS ADVANCED FEATURES - SIMPLE TEST SUITE")
    print("="*60)

    tests = [
        test_schemas,
        test_causal_attention,
        test_performance_logger,
        test_enhanced_agents,
        test_brain_visualizer,
        test_reloader
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

        print()

    print("="*60)
    print(f"RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Advanced features are working correctly.")
    else:
        print(f"⚠️  {total - passed} tests failed. Check the error messages above.")

    print("="*60)

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)