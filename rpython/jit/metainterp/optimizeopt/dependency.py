
from rpython.jit.metainterp.resoperation import rop

class Dependency(object):
    def __init__(self, index):
        self.index = index

class CrossIterationDependency(Dependency):
    pass

class DependencyGraph(object):
    """ A graph that represents one of the following dependencies:
          * True dependency
          * Anti dependency
          * Ouput dependency
        Representation is an adjacent list. The number of edges between the
        vertices is expected to be small.
    """
    def __init__(self, optimizer, loop):
        self.loop = loop
        self.operations = loop.operations
        self.optimizer = optimizer
        self.adjacent_list = [ [] ] * len(self.operations)

    def instr_dependency(self, from_instr_idx, to_instr_idx):
        """ Does there exist a dependency from the instruction to another?
            Returns None if there is no dependency or the Dependency object in
            any other case.
        """
        edges = self.adjacent_list[from_instr_idx]
        for edge in edges:
            if edge.index == to_instr_idx:
                return edge
        return None 

