

RETURNS_LOCAL_POINTER = set([
    'malloc', 'malloc_varsize', 'malloc_nonmovable',
    'malloc_nonmovable_varsize',
    ])


class StmLocalTracker(object):
    """Tracker to determine which pointers are statically known to point
    to local objects.  Here, 'local' versus 'global' is meant in the sense
    of the stmgc: a pointer is 'local' if it goes to the thread-local memory,
    and 'global' if it points to the shared read-only memory area."""

    def __init__(self, translator):
        self.translator = translator
        # a set of variables in the graphs that contain a known-to-be-local
        # pointer.
        self.locals = set()

    def track_and_propagate_locals(self):
        for graph in self.translator.graphs:
            self.propagate_from_graph(graph)

    def propagate_from_graph(self, graph):
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname in RETURNS_LOCAL_POINTER:
                    self.locals.add(op.result)
