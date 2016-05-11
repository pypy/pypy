from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.flowspace.model import mkentrymap
from rpython.flowspace.model import Variable, Constant, SpaceOperation
from rpython.tool.algo.regalloc import perform_register_allocation
from rpython.translator.unsimplify import varoftype


def is_trivial_rewrite(op):
    return op.opname in ('same_as', 'cast_pointer', 'cast_opaque_ptr')


def find_predecessors(graph, pending_pred):
    """Return the set of variables whose content can end up inside one
    of the 'pending_pred', which is a list of (block, var) tuples.
    """
    entrymap = mkentrymap(graph)
    pred = set([v for block, v in pending_pred])

    def add(block, v):
        if isinstance(v, Variable):
            if v not in pred:
                pending_pred.append((block, v))
                pred.add(v)

    while pending_pred:
        block, v = pending_pred.pop()
        if v in block.inputargs:
            var_index = block.inputargs.index(v)
            for link in entrymap[block]:
                prevblock = link.prevblock
                if prevblock is not None:
                    add(prevblock, link.args[var_index])
        else:
            for op in block.operations:
                if op.result is v:
                    if is_trivial_rewrite(op):
                        add(block, op.args[0])
                    break
    return pred


def find_successors(graph, pending_succ):
    """Return the set of variables where one of the 'pending_succ' can
    end up.  'block_succ' is a list of (block, var) tuples.
    """
    succ = set([v for block, v in pending_succ])

    def add(block, v):
        if isinstance(v, Variable):
            if v not in succ:
                pending_succ.append((block, v))
                succ.add(v)

    while pending_succ:
        block, v = pending_succ.pop()
        for op in block.operations:
            if op.args and v is op.args[0] and is_trivial_rewrite(op):
                add(block, op.result)
        for link in block.exits:
            for i, v1 in enumerate(link.args):
                if v1 is v:
                    add(link.target, link.target.inputargs[i])
    return succ


def find_interesting_variables(graph):
    # Decide which variables are "interesting" or not.  Interesting
    # variables contain at least the ones that appear in gc_push_roots
    # and gc_pop_roots.
    pending_pred = []
    pending_succ = []
    interesting_vars = set()
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'gc_push_roots':
                for v in op.args:
                    interesting_vars.add(v)
                    pending_pred.append((block, v))
            elif op.opname == 'gc_pop_roots':
                for v in op.args:
                    assert v in interesting_vars   # must be pushed just above
                    pending_succ.append((block, v))
    if not interesting_vars:
        return None

    # If there is a path from a gc_pop_roots(v) to a subsequent
    # gc_push_roots(w) where w contains the same value as v along that
    # path, then we consider all intermediate blocks along that path
    # which contain a copy of the same value, and add these variables
    # as "interesting", too.  Formally, a variable in a block is
    # "interesting" if it is both a "predecessor" and a "successor",
    # where predecessors are variables which (sometimes) end in a
    # gc_push_roots, and successors are variables which (sometimes)
    # come from a gc_pop_roots.
    pred = find_predecessors(graph, pending_pred)
    succ = find_successors(graph, pending_succ)
    interesting_vars |= (pred & succ)

    return interesting_vars


def allocate_registers(graph):
    interesting_vars = find_interesting_variables(graph)
    if not interesting_vars:
        return None
    regalloc = perform_register_allocation(graph, interesting_vars.__contains__)
    regalloc.find_num_colors()
    return regalloc


def _gc_save_root(index, var):
    c_index = Constant(index, lltype.Signed)
    return SpaceOperation('gc_save_root', [c_index, var],
                          varoftype(lltype.Void))

c_NULL = Constant(lltype.nullptr(llmemory.GCREF.TO), llmemory.GCREF)

def make_bitmask(filled):
    n = filled.count(False)
    if n == 0:
        return (None, None)
    if n == 1:
        return (filled.index(False), c_NULL)
    bitmask = 0
    last_index = 0
    for i in range(len(filled)):
        if not filled[i]:
            bitmask <<= (i - last_index)
            last_index = i
            bitmask |= 1
    return (last_index, Constant(bitmask, lltype.Signed))


def expand_one_push_roots(regalloc, args):
    if regalloc is None:
        assert len(args) == 0
    else:
        filled = [False] * regalloc.numcolors
        for v in args:
            index = regalloc.getcolor(v)
            assert not filled[index]
            filled[index] = True
            yield _gc_save_root(index, v)
        bitmask_index, bitmask_v = make_bitmask(filled)
        if bitmask_index is not None:
            yield _gc_save_root(bitmask_index, bitmask_v)


def expand_push_roots(graph, regalloc):
    """Expand gc_push_roots into a series of gc_save_root, including
    writing a bitmask tag to mark some entries as not-in-use
    """
    for block in graph.iterblocks():
        any_change = False
        newops = []
        for op in block.operations:
            if op.opname == 'gc_push_roots':
                newops += expand_one_push_roots(regalloc, op)
                any_change = True
            else:
                newops.append(op)
        if any_change:
            block.operations = newops


def move_pushes_earlier(graph, regalloc):
    """gc_push_roots and gc_pop_roots are pushes/pops to the shadowstack,
    immediately enclosing the operation that needs them (typically a call).
    Here, we try to move individual pushes earlier, in fact as early as
    possible under the following conditions: we only move it across vars
    that are 'interesting_vars'; and we stop when we encounter the
    operation that produces the value, or when we encounter a gc_pop_roots.
    In the latter case, if that gc_pop_roots pops the same value out of the
    same stack location, then success: we can remove the gc_push_root on
    that path.

    If the process succeeds to remove the gc_push_root along at least
    one path, we generate it explicitly on the other paths, and we
    remove the original gc_push_root.  If the process doesn't succeed
    in doing any such removal, we don't do anything.
    """
    # Concrete example (assembler tested on x86-64 gcc 5.3 and clang 3.7):
    #
    # ----original----           ----move_pushes_earlier----
    #
    # while (a > 10) {           *foo = b;
    #     *foo = b;              while (a > 10) {
    #     a = g(a);                  a = g(a);
    #     b = *foo;                  b = *foo;
    #                                // *foo = b;
    # }                          }
    # return b;                  return b;
    #
    # => the store and the       => the store is before, and gcc/clang
    # load are in the loop,      moves the load after the loop
    # even in the assembler      (the commented-out '*foo=b' is removed
    #                            by this function, but gcc/clang would
    #                            also remove it)

    x.x.x.x


def expand_push_pop_roots(graph):
    xxxxxxxxx
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'gc_push_roots':
                for v in op.args:
                    interesting_vars.add(v)
                    pending_pred.append((block, v))
            elif op.opname == 'gc_pop_roots':
                for v in op.args:
                    assert v in interesting_vars   # must be pushed just above
                    pending_succ.append((block, v))


def postprocess_graph(gct, graph):
    """Collect information about the gc_push_roots and gc_pop_roots
    added in this complete graph, and replace them with real operations.
    """
    regalloc = allocate_registers(graph)
    xxxx
