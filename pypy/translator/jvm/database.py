"""
For now, a simple worklist abstraction.
"""

class Database:
    def __init__(self):
        self._pending = []
        
    def pending_node(self, node):
        self._pending.append(node)

    def len_pending(self):
        return len(self._pending)

    def pop(self):
        return self._pending.pop()

    def method_for_graph(self, graph):
        
