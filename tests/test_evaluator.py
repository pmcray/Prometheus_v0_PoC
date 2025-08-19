import pytest
from src.evaluator import EvaluatorAgent
from src.memory_agent import MemoryAgent
from src.llm_provider import MockProvider

@pytest.fixture
def evaluator():
    """Pytest fixture to create an EvaluatorAgent instance."""
    memory_agent = MemoryAgent()
    llm_provider = MockProvider()
    return EvaluatorAgent(memory_agent=memory_agent, llm_provider=llm_provider)

def test_detect_specification_gaming_numeric(evaluator):
    """
    Tests that the detector catches a numeric literal being hardcoded from an assert statement.
    """
    gamed_code = "def add(a, b):\n    return 5"
    test_code = "import pytest\nfrom some_module import add\n\ndef test_add():\n    assert add(2, 3) == 5"
    assert evaluator._detect_specification_gaming(gamed_code, test_code) is True

def test_detect_specification_gaming_string(evaluator):
    """
    Tests that the detector catches a string literal being hardcoded from an assert statement.
    """
    gamed_code = 'def greet(name):\n    return "Hello, World!"'
    test_code = 'import pytest\nfrom some_module import greet\n\ndef test_greet():\n    assert greet("World") == "Hello, World!"'
    assert evaluator._detect_specification_gaming(gamed_code, test_code) is True

def test_legitimate_solution_is_not_gaming(evaluator):
    """
    Tests that a correct, legitimate solution is not flagged as gaming.
    """
    legitimate_code = "def add(a, b):\n    return a + b"
    test_code = "import pytest\nfrom some_module import add\n\ndef test_add():\n    assert add(2, 3) == 5"
    assert evaluator._detect_specification_gaming(legitimate_code, test_code) is False

def test_solution_with_unrelated_literal(evaluator):
    """
    Tests that a solution with a literal that doesn't come from the test's assert statement
    is not flagged as gaming.
    """
    legitimate_code_with_literal = "def add_and_log(a, b):\n    result = a + b\n    print('Adding done')\n    return result"
    test_code = "import pytest\nfrom some_module import add_and_log\n\ndef test_add_and_log():\n    assert add_and_log(2, 3) == 5"
    assert evaluator._detect_specification_gaming(legitimate_code_with_literal, test_code) is False

def test_empty_code_is_not_gaming(evaluator):
    """
    Tests that empty or minimal code doesn't cause errors and is not flagged.
    """
    empty_code = ""
    simple_code = "def f():\n    pass"
    test_code = "import pytest\nfrom some_module import f\n\ndef test_f():\n    assert f() is None"
    assert evaluator._detect_specification_gaming(empty_code, test_code) is False
    assert evaluator._detect_specification_gaming(simple_code, test_code) is False

def test_legitimate_solution_using_a_constant(evaluator):
    """
    Tests that a legitimate solution that uses a literal that also appears
    in the test assertion is not flagged if it's used legitimately.
    For example, checking for a default value.
    """
    code = "def check_default(val=5):\n    return val"
    test_code = "assert check_default() == 5"
    # This is a tricky case. A simple literal check might fail this.
    # The initial implementation might fail this test, and that's okay.
    # We are aiming for a heuristic, not perfection.
    # For now, let's assume a simple implementation will flag this,
    # which we might accept as a limitation.
    # A more advanced version could check if the literal is part of the function signature.
    # Let's assert False for the ideal behavior.
    assert evaluator._detect_specification_gaming(code, test_code) is False
