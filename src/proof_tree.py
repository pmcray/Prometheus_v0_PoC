import logging

class ProofNode:
    def __init__(self, state, tactic=None, parent=None):
        self.state = state
        self.tactic = tactic
        self.parent = parent
        self.children = []
        self.is_solved = state.is_complete()

    def add_child(self, child_node):
        self.children.append(child_node)

    def __repr__(self):
        return f"ProofNode(tactic={self.tactic}, solved={self.is_solved})"

class ProofTree:
    def __init__(self, root_state):
        self.root = ProofNode(root_state)
        logging.info("ProofTree initialized.")

    def find_most_promising_node(self):
        """
        Finds the most promising, unsolved leaf node to expand next.
        """
        if not self.root.is_solved and not self.root.children:
            return self.root
            
        nodes_to_visit = [self.root]
        while nodes_to_visit:
            current_node = nodes_to_visit.pop(0)
            if not current_node.is_solved and not current_node.children:
                return current_node
            nodes_to_visit.extend(current_node.children)
        return None

    def add_node(self, state, tactic, parent_node):
        new_node = ProofNode(state, tactic, parent_node)
        parent_node.add_child(new_node)
        return new_node

    def get_proof_path(self, node):
        """
        Returns the sequence of tactics from the root to the given node.
        """
        path = []
        current = node
        while current.parent:
            path.append(current.tactic)
            current = current.parent
        return list(reversed(path))