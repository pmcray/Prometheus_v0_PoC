

import os
import logging
from src.auditor_agent import AuditorAgent
from src.proof_tree import ProofTree, ProofNode
from src.tools import ProofState

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

def main():
    logging.info("--- Verifying AuditorAgent ---")
    
    # 1. Create a mock ProofTree
    root_state = ProofState("1 goal\n⊢ a + b + c = a + (b + c)")
    tree = ProofTree(root_state)
    node1 = tree.add_node(ProofState("2 goals..."), "induction a", tree.root)
    node2 = tree.add_node(ProofState("1 goal..."), "simp", node1)
    node3 = tree.add_node(ProofState("goals accomplished"), "rw [Nat.add_assoc]", node2)
    
    # 2. Instantiate the AuditorAgent
    auditor = AuditorAgent(api_key=API_KEY)
    
    # 3. Generate the audit trail
    theorem = "theorem add_assoc (a b c : Nat) : a + b + c = a + (b + c)"
    audit_trail = auditor.generate_audit_trail(tree, theorem)
    
    logging.info(audit_trail)

if __name__ == "__main__":
    main()

