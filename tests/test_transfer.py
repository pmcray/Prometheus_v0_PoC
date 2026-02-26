"""
Tests for CrossDomainTransferLearner — WP-05 Verification
"""

import pytest
import os
import json
from prometheus.transfer import CrossDomainTransferLearner

def test_transfer_learner_extracts_primitives():
    # Setup - Use mock directory to avoid side effects
    storage = "test_transfer_data"
    if not os.path.exists(storage):
        os.makedirs(storage)
        
    learner = CrossDomainTransferLearner(storage_dir=storage)
    
    # Mock performance data
    chess_data = {
        "win_rate": 0.75,
        "avg_game_length": 45,
        "common_moves": ["e2e4", "d2d4"]
    }
    
    # Primitives will be mocked since we're using LLMBackend placeholder
    prims = learner.extract_strategic_primitives("chess", chess_data)
    assert len(prims) > 0
    assert "chess" in learner.knowledge_base
    
    # Verify persistence
    learner2 = CrossDomainTransferLearner(storage_dir=storage)
    assert "chess" in learner2.knowledge_base
    assert learner2.knowledge_base["chess"] == prims

def test_cross_domain_suggestions():
    storage = "test_transfer_data"
    learner = CrossDomainTransferLearner(storage_dir=storage)
    
    # Manually seed knowledge base for Go
    learner.knowledge_base["go"] = ["territory_control", "connectivity", "liberty_counting"]
    learner.save_knowledge()
    
    # Suggest for Chess based on Go knowledge
    suggestions = learner.suggest_cross_domain_strategy("chess")
    assert len(suggestions) > 0
    # Our LLM placeholder will return something
    assert isinstance(suggestions, str)
