from rpython.jit.metainterp.resoperation import rop

class Dependency(object):
    def __init__(self, idx_from, idx_to, arg, is_definition):
        self.defined_arg = arg
        self.idx_from = idx_from 
        self.idx_to = idx_to
        self.is_definition = is_definition

    def __repr__(self):
        return 'Dep(trace[%d] -> trace[%d], arg: %s, def-use? %d)' \
                % (self.idx_from, self.idx_to, self.defined_arg, \
                   self.is_definition)

class DependencyGraph(object):
    """ A graph that represents one of the following dependencies:
          * True dependency
          * Anti dependency
          * Ouput dependency
        Representation is an adjacent list. The number of edges between the
        vertices is expected to be small.
    """
    def __init__(self, trace):
        self.trace = trace
        self.operations = self.trace.operations
        self.adjacent_list = [ [] for i in range(len(self.operations)) ]

        self.build_dependencies(self.operations)

    def build_dependencies(self, operations):
        """ This is basically building the definition-use chain and saving this
            information in a graph structure. This is the same as calculating
            the reaching definitions and the 'looking back' whenever it is used.

            Write After Read, Write After Write dependencies are not possible,
            the operations are in SSA form
        """
        defining_indices = {}

        for i,op in enumerate(operations):
            # the label operation defines all operations at the
            # beginning of the loop
            if op.getopnum() == rop.LABEL:
                for arg in op.getarglist():
                    defining_indices[arg] = 0
                continue # prevent adding edge to the label itself

            # TODO what about a JUMP operation? it often has many parameters
            # (10+) and uses  nearly every definition in the trace (for loops).
            # Maybe we can skip this operation and let jump NEVER move...

            if op.result is not None:
                # the trace is always in SSA form, thus it is neither possible to have a WAR
                # not a WAW dependency
                defining_indices[op.result] = i

            for arg in op.getarglist():
                if arg in defining_indices:
                    idx = defining_indices[arg]
                    self._put_edge(idx, i, arg)

            if op.getfailargs():
                for arg in op.getfailargs():
                    if arg in defining_indices:
                        idx = defining_indices[arg]
                        self._put_edge(idx, i, arg)

    def _put_edge(self, idx_from, idx_to, arg):
        if self._is_unique_dep(idx_from, idx_to, arg):
            self.adjacent_list[idx_from].append(Dependency(idx_from, idx_to, arg, True))
            self.adjacent_list[idx_to].append(Dependency(idx_to, idx_from, arg, False))

    def _is_unique_dep(self, idx_from, idx_to, arg):
        """ Dependencies must be unique. It is not allowed
        to have multiple dependencies.
        e.g. label(i1)
             i2 = int_add(i1,i1)
             ...

        Only the label instr can only have one dep (0->1) even if it is
        used twice in int_add. The same is true for the reverse dependency
        (1<-0) at int_add.
        """
        for dep in self.adjacent_list[idx_from]:
            if dep.idx_from == idx_from and dep.idx_to == idx_to \
               and dep.defined_arg == arg:
                return False
        return True

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

