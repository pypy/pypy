from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.flowspace.model import mkentrymap, checkgraph
from rpython.flowspace.model import Variable, Constant, SpaceOperation
from rpython.tool.algo.regalloc import perform_register_allocation
from rpython.tool.algo.unionfind import UnionFind
from rpython.translator.unsimplify import varoftype, insert_empty_block
from rpython.translator.simplify import join_blocks
from collections import defaultdict


def is_trivial_rewrite(op):
    return (op.opname in ('same_as', 'cast_pointer', 'cast_opaque_ptr')
                and isinstance(op.args[0], Variable))


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

def _gc_restore_root(index, var):
    c_index = Constant(index, lltype.Signed)
    return SpaceOperation('gc_restore_root', [c_index, var],
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
    assert bitmask & 1
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
        bitmask_index, bitmask_c = make_bitmask(filled)
        if bitmask_index is not None:
            yield _gc_save_root(bitmask_index, bitmask_c)

def expand_one_pop_roots(regalloc, args):
    if regalloc is None:
        assert len(args) == 0
    else:
        for v in args:
            index = regalloc.getcolor(v)
            yield _gc_restore_root(index, v)


def expand_push_roots(graph, regalloc):
    """Expand gc_push_roots into a series of gc_save_root, including
    writing a bitmask tag to mark some entries as not-in-use.
    (If regalloc is None, it will still remove empty gc_push_roots.)
    """
    for block in graph.iterblocks():
        any_change = False
        newops = []
        for op in block.operations:
            if op.opname == 'gc_push_roots':
                newops += expand_one_push_roots(regalloc, op.args)
                any_change = True
            else:
                newops.append(op)
        if any_change:
            block.operations = newops


def move_pushes_earlier(graph, regalloc):
    """gc_push_roots and gc_pop_roots are pushes/pops to the shadowstack,
    immediately enclosing the operation that needs them (typically a call).
    Here, we try to move individual pushes earlier.

    Should run after expand_push_roots(), but before expand_pop_roots(),
    so that it sees individual 'gc_save_root' operations but bulk
    'gc_pop_roots' operations.
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
    #                            here, but gcc/clang would also remove it)

    # Draft of the algorithm: see shadowcolor.txt

    if not regalloc:
        return

    entrymap = mkentrymap(graph)
    inputvars = {}    # {inputvar: (its block, its index in inputargs)}
    for block in graph.iterblocks():
        for i, v in enumerate(block.inputargs):
            inputvars[v] = (block, i)

    Plist = []

    for index in range(regalloc.numcolors):
        U = UnionFind()

        S = set()
        for block in graph.iterblocks():
            for op in reversed(block.operations):
                if op.opname == 'gc_pop_roots':
                    break
            else:
                continue   # no gc_pop_roots in this block
            for v in op.args:
                if regalloc.getcolor(v) == index:
                    break
            else:
                continue   # no variable goes into index i

            succ = set()
            pending_succ = [(block, v)]
            while pending_succ:
                block1, v1 = pending_succ.pop()
                for op1 in block1.operations:
                    if is_trivial_rewrite(op1) and op1.args[0] is v1:
                        pending_succ.append((block1, op1.result))
                for link1 in block1.exits:
                    for i2, v2 in enumerate(link1.args):
                        if v2 is not v1:
                            continue
                        block2 = link1.target
                        w2 = block2.inputargs[i2]
                        if w2 in succ:
                            continue
                        succ.add(w2)
                        # XXX renaming
                        for op2 in block2.operations:
                            if op2.opname in ('gc_save_root', 'gc_pop_roots'):
                                break
                        else:
                            pending_succ.append((block2, w2))
            U.union_list(list(succ))
            S.update(succ)

        G = defaultdict(set)
        for block in graph.iterblocks():
            for op in block.operations:
                # XXX handle renames
                if op.opname == 'gc_save_root' and op.args[0].value == index:
                    break
            else:
                continue   # no matching gc_save_root in this block

            key = (block, op)
            pred = set()
            pending_pred = [(block, op.args[1])]
            while pending_pred:
                block1, v1 = pending_pred.pop()
                if v1 not in block1.inputargs:
                    # XXX handle renames
                    pass
                else:
                    pred.add(v1)
                    varindex = block1.inputargs.index(v1)
                    for link1 in entrymap[block1]:
                        prevblock1 = link1.prevblock
                        if prevblock1 is not None:
                            w1 = link1.args[varindex]
                            if w1 not in pred:
                                pending_pred.append((prevblock1, w1))
            U.union_list(list(pred))
            for v1 in pred:
                G[v1].add(key)

        M = S.intersection(G)

        parts_target = {}
        for v in M:
            vp = U.find_rep(v)
            if vp not in parts_target:
                new_part = (index, set(), set())
                # (index,
                #  subset P of variables,
                #  set of (block, gc_save_root))
                Plist.append(new_part)
                parts_target[vp] = new_part
            part = parts_target[vp]
            part[1].add(v)
            part[2].update(G[v])

    #P.sort(...heuristic?)

    variables_along_changes = set()

    for i, P, gcsaveroots in Plist:
        if variables_along_changes.intersection(P):
            continue
        if any(op not in block.operations for block, op in gcsaveroots):
            continue

        success = False
        mark = []

        for v in P:
            block, varindex = inputvars[v]
            for link in entrymap[block]:
                w = link.args[varindex]
                maybe_found = regalloc.checkcolor(w, i)  # unless proven false
                if link.prevblock is None:
                    maybe_found = False
                if maybe_found:
                    search = set([w])
                    for op in reversed(link.prevblock.operations):
                        if op.opname == 'gc_pop_roots':
                            if search.intersection(op.args):
                                success = True
                            else:
                                maybe_found = False
                            break
                        if (is_trivial_rewrite(op) and op.result in search
                                and regalloc.checkcolor(op.args[0], i)):
                            search.add(op.args[0])
                    else:
                        maybe_found = False
                if not maybe_found:
                    if w not in P:
                        mark.append((link, varindex))

        if success:
            for block, op in gcsaveroots:
                newops = list(block.operations)
                newops.remove(op)
                block.operations = newops

            for link, varindex in mark:
                newblock = insert_empty_block(link)
                v = newblock.inputargs[varindex]
                newblock.operations.append(_gc_save_root(i, v))

            variables_along_changes.update(P)

    if variables_along_changes:     # if there was any change
        checkgraph(graph)
        join_blocks(graph)


def expand_pop_roots(graph, regalloc):
    """gc_pop_roots => series of gc_restore_root; this is done after
    move_pushes_earlier() because that one doesn't work correctly if
    a completely-empty gc_pop_roots is removed.

    Also notice in-block code sequences like gc_pop_roots(v) followed
    by a gc_save_root(v), and drop the gc_save_root.
    """
    drop = {}
    for block in graph.iterblocks():
        any_change = False
        newops = []
        for op in block.operations:
            if op.opname == 'gc_pop_roots':
                expanded = list(expand_one_pop_roots(regalloc, op.args))
                drop = {}
                for op1 in expanded:
                    drop[op1.args[1]] = op1.args[0].value
                newops += expanded
                any_change = True
            elif (op.opname == 'gc_save_root' and
                      drop.get(op.args[1]) == op.args[0].value):
                any_change = True    # kill the operation
            else:
                newops.append(op)
        if any_change:
            block.operations = newops


def postprocess_graph(gct, graph):
    """Collect information about the gc_push_roots and gc_pop_roots
    added in this complete graph, and replace them with real operations.
    """
    regalloc = allocate_registers(graph)
    expand_push_roots(graph, regalloc)
    move_pushes_earlier(graph, regalloc)
    expand_pop_roots(graph, regalloc)
    xxxx
