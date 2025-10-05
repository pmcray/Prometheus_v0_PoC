"""
Direct test of individual components without package imports
"""

import sys
import os

# Test direct imports
def test_direct_imports():
    """Test direct imports of key components"""

    try:
        print("Testing direct imports...")

        # Test causal attention
        sys.path.insert(0, 'prometheus')

        from causal_attention import CausalAttentionHead, ASTComplexityAnalyzer
        print("✅ Causal Attention imported")

        # Test analyzer
        analyzer = ASTComplexityAnalyzer()
        code = "def test():\n    for i in range(10):\n        for j in range(10):\n            pass"
        result = analyzer.analyze_complexity(code)
        print(f"✅ AST Analysis result: {result.get('max_loop_depth', 0)} loop depth")

        # Test enhanced performance logger
        from enhanced_performance_logger import EnhancedPerformanceLogger
        print("✅ Enhanced Performance Logger imported")

        # Test brain visualizer
        from brain_visualizer import BrainMapVisualizer
        visualizer = BrainMapVisualizer()
        print("✅ Brain Visualizer imported and initialized")

        # Test enhanced reloader
        from enhanced_reloader import EnhancedModuleReloader
        reloader = EnhancedModuleReloader()
        print("✅ Enhanced Reloader imported and initialized")

        return True

    except Exception as e:
        print(f"❌ Direct import failed: {e}")
        return False

def test_functionality():
    """Test basic functionality"""

    try:
        print("\nTesting functionality...")

        # Add prometheus to path
        sys.path.insert(0, 'prometheus')

        # Test AST analysis
        from causal_attention import ASTComplexityAnalyzer
        analyzer = ASTComplexityAnalyzer()

        test_code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""

        analysis = analyzer.analyze_complexity(test_code)
        print(f"✅ Complexity analysis: {analysis}")

        # Test causal attention head
        from causal_attention import CausalAttentionHead
        attention = CausalAttentionHead()

        focus = attention.generate_causal_focus(test_code, "Optimize bubble sort")
        print(f"✅ Causal focus generated with {len(focus.get('attention_targets', []))} targets")

        # Test performance logger
        from enhanced_performance_logger import EnhancedPerformanceLogger
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            logger = EnhancedPerformanceLogger(temp_dir)
            run_id = logger.start_run("Test run")
            logger.log_metric("test_metric", 123.45)
            logger.end_run("completed")

            run_log = logger.get_run_log(run_id)
            print(f"✅ Performance logging: Run {run_id} status = {run_log['status']}")

        # Test visualizer HTML generation
        from brain_visualizer import BrainMapVisualizer
        visualizer = BrainMapVisualizer()
        html = visualizer.generate_brain_map_html()

        print(f"✅ Brain map HTML generated: {len(html)} characters")

        return True

    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the tests"""
    print("="*60)
    print("PROMETHEUS ADVANCED - DIRECT COMPONENT TESTS")
    print("="*60)

    # Change to project directory
    os.chdir('/home/pmc/Prometheus_v0_PoC')

    tests_passed = 0
    total_tests = 2

    if test_direct_imports():
        tests_passed += 1

    if test_functionality():
        tests_passed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("🎉 All direct tests passed! Core components are working.")
    else:
        print(f"⚠️ {total_tests - tests_passed} test(s) failed.")

    print("="*60)

    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)