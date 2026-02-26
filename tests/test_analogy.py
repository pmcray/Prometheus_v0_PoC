"""
Tests for AnalogicalSearchEngine — WP-08 Verification
"""

import pytest
import os
import json
from prometheus.strange_loop.analogy import AnalogicalSearchEngine

def test_skeleton_extraction_and_analogy():
    storage = "logs/test_analogy_memory.json"
    if os.path.exists(storage):
        os.remove(storage)
        
    engine = AnalogicalSearchEngine(storage_path=storage)
    
    # 1. Record an experience in Domain A (Logistics)
    engine.record_experience(
        domain="logistics",
        problem="Deliver 10 packages using 2 trucks with minimum fuel.",
        solution="def optimize_routes(packages, trucks): # cluster by location..."
    )
    
    # 2. Try to find an analogy for Domain B (Data Processing)
    # A problem about partitioning data could be structurally similar to truck loading
    analogy = engine.find_analogy(
        target_domain="data_processing",
        target_problem="Partition 1000 records into 5 batches for parallel processing."
    )
    
    # Since we use the LLM placeholder, it will return a match based on the 
    # deterministic placeholder string.
    assert analogy is not None
    assert analogy["domain"] == "logistics"
    assert "skeleton" in analogy
    
    # Cleanup
    if os.path.exists(storage):
        os.remove(storage)

def test_no_analogy_for_same_domain():
    engine = AnalogicalSearchEngine(storage_path="logs/tmp_memory.json")
    engine.record_experience("domain_x", "prob_1", "sol_1")
    
    # Should not find analogy in the same domain
    match = engine.find_analogy("domain_x", "prob_2")
    assert match is None
    
    if os.path.exists("logs/tmp_memory.json"):
        os.remove("logs/tmp_memory.json")
