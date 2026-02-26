"""
Tests for HierarchicalKB and IsomorphismMapper — WP-07 Verification
"""

import pytest
from prometheus.knowledge.hierarchical_kb import HierarchicalKnowledgeBase, KnowledgeSymbol
from prometheus.knowledge.isomorphism import IsomorphismMapper

def test_kb_chunking():
    kb = HierarchicalKnowledgeBase()
    
    # Create a 'lemma' from existing axioms
    kb.create_chunk(
        "recursive_optimization", 
        ["recursion", "pure_function"],
        "Optimizing code by using pure recursive calls."
    )
    
    assert "recursive_optimization" in kb.symbols
    assert kb.symbols["recursive_optimization"].level == 1
    assert "recursion" in kb.symbols["recursive_optimization"].dependencies

def test_isomorphism_fidelity():
    kb = HierarchicalKnowledgeBase()
    mapper = IsomorphismMapper(kb)
    
    # Mock environment data
    env_data = {
        "predictions": [1, 0, 1],
        "actuals": [1, 0, 0] # 2/3 accuracy
    }
    
    report = mapper.compute_fidelity_score(env_data)
    
    assert "isomorphism_fidelity" in report
    assert report["predictive_accuracy"] == pytest.approx(0.666, abs=0.01)
    # Descriptive efficiency should be 0 because we haven't created chunks yet
    assert report["descriptive_efficiency"] == 0.0
    
    # Add a chunk and check efficiency improvement
    kb.create_chunk("test_chunk", ["pure_function"], "test")
    report2 = mapper.compute_fidelity_score(env_data)
    assert report2["descriptive_efficiency"] > 0.0
