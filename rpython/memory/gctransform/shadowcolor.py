

def find_interesting_variables(graph):
    # Decide which variables are "interesting" or not.  Interesting
    # variables contain at least the ones that appear in gc_push_roots
    # and gc_pop_roots.
    pending = []
    interesting_vars = set()
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'gc_push_roots':
                for v in op.args:
                    interesting_vars.add(v)
                    pending.append((block, v))
            elif op.opname == 'gc_pop_roots':
                for v in op.args:
                    assert v in interesting_vars   # must be pushed just above
    if not interesting_vars:
        return

    # If there is a path from a gc_pop_roots(v) to a subsequent
    # gc_push_roots(w) where w contains the same value as v along that
    # path, then we consider all intermediate blocks along that path
    # which contain a copy of the same value, and add these variables
    # as "interesting", too.

    #....
    return interesting_vars


def postprocess_graph(gct, graph):
    """Collect information about the gc_push_roots and gc_pop_roots
    added in this complete graph, and replace them with real operations.
    """
    xxxx
