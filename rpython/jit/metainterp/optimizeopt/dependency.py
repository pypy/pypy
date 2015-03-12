from rpython.jit.metainterp.resoperation import rop

class Dependency(object):
    def __init__(self, idx_from, idx_to, arg, is_definition):
        self.defined_arg = arg
        self.idx_from = idx_from 
        self.idx_to = idx_to
        self.is_definition = is_definition

    def __repr__(self):
        return 'dep(%d -> %d, defines? %d)' % (self.idx_from, self.idx_to, self.is_definition)

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
        self.adjacent_list = [ [] for i in range(len(self.operations)) ]

        self.build_dependencies(loop.operations)

    def build_dependencies(self, operations):
        """ This is basically building the definition-use chain and saving this
            information in a graph structure. This is the same as calculating
            the reaching definitions and the 'looking back' whenever it is used.

            Write After Read, Write After Write dependencies are not possible,
            the operations are in SSA form
        """
        defining_indices = {}

        for i,op in enumerate(operations):
            # the label operation defines all operations at the beginning of the loop
            if op.getopnum() == rop.LABEL:
                for arg in op.getarglist():
                    defining_indices[arg] = 0
                continue # prevent adding edge to the label itself

            # TODO what about a JUMP operation? it often has many parameters (10+) and uses
            # nearly every definition in the trace (for loops). Maybe we can skip this operation

            if op.result is not None:
                # the trace is always in SSA form, thus it is neither possible to have a WAR
                # not a WAW dependency
                defining_indices[op.result] = i

            for arg in op.getarglist():
                if arg in defining_indices:
                    idx = defining_indices[arg]
                    self._put_edge(idx, i, arg)

    def _put_edge(self, idx_from, idx_to, arg):
        self.adjacent_list[idx_from].append(Dependency(idx_from, idx_to, arg, True))
        self.adjacent_list[idx_to].append(Dependency(idx_to, idx_from, arg, False))

    def instr_dependencies(self, idx):
        edges = self.adjacent_list[idx]
        return edges

    def instr_dependency(self, from_instr_idx, to_instr_idx):
        """ Does there exist a dependency from the instruction to another?
            Returns None if there is no dependency or the Dependency object in
            any other case.
        """
        for edge in self.instr_dependencies(from_instr_idx):
            if edge.idx_to == to_instr_idx:
                return edge
        return None 

