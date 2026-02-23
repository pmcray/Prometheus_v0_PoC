
import pytest
from prometheus.causal_agentic_mesh import CausalAgenticMesh

@pytest.fixture
def mesh():
    return CausalAgenticMesh()

def test_mesh_node_addition(mesh):
    mesh.add_node("agent_1", "agent", description="A test agent")
    assert "agent_1" in mesh.nodes
    assert mesh.nodes["agent_1"].node_type == "agent"
    assert mesh.graph.has_node("agent_1")

def test_mesh_edge_addition(mesh):
    mesh.add_node("n1", "observation")
    mesh.add_node("n2", "agent")
    mesh.add_edge("n1", "n2", "causes", strength=0.8)
    
    assert len(mesh.edges) == 1
    assert mesh.graph.has_edge("n1", "n2")
    assert mesh.graph.edges["n1", "n2"]["edge_type"] == "causes"
    assert mesh.graph.edges["n1", "n2"]["strength"] == 0.8

def test_causal_chain_tracing(mesh):
    mesh.add_node("A", "observation")
    mesh.add_node("B", "agent")
    mesh.add_node("C", "decision")
    mesh.add_edge("A", "B", "causes")
    mesh.add_edge("B", "C", "causes")
    
    chains = mesh.get_causal_chain("C")
    assert len(chains) == 1
    assert chains[0] == ["A", "B", "C"]

def test_critical_path(mesh):
    mesh.add_node("start", "observation")
    mesh.add_node("mid1", "agent")
    mesh.add_node("mid2", "agent")
    mesh.add_node("end", "decision")
    
    # Path 1: strength 0.5 + 0.5 = 1.0
    mesh.add_edge("start", "mid1", "causes", strength=0.5)
    mesh.add_edge("mid1", "end", "causes", strength=0.5)
    
    # Path 2: strength 0.9 + 0.9 = 1.8 (Critical)
    mesh.add_edge("start", "mid2", "causes", strength=0.9)
    mesh.add_edge("mid2", "end", "causes", strength=0.9)
    
    path = mesh.find_critical_path("start", "end")
    assert path == ["start", "mid2", "end"]

def test_bottleneck_identification(mesh):
    # Create a 'star' or 'hub' pattern
    mesh.add_node("hub", "agent")
    for i in range(5):
        node_id = f"leaf_{i}"
        mesh.add_node(node_id, "observation")
        mesh.add_edge(node_id, "hub", "informs")
        
    mesh.add_node("output", "decision")
    mesh.add_edge("hub", "output", "causes")
    
    bottlenecks = mesh.identify_bottlenecks(threshold=3)
    assert "hub" in bottlenecks
