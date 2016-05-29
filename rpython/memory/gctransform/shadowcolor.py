from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.flowspace.model import mkentrymap, checkgraph, Block, Link
from rpython.flowspace.model import Variable, Constant, SpaceOperation
from rpython.tool.algo.regalloc import perform_register_allocation
from rpython.tool.algo.unionfind import UnionFind
from rpython.translator.unsimplify import varoftype, insert_empty_block
from rpython.translator.unsimplify import insert_empty_startblock, split_block
from rpython.translator.simplify import join_blocks
from rpython.rlib.rarithmetic import intmask
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
                    if not isinstance(v, Variable):
                        continue
                    interesting_vars.add(v)
                    pending_pred.append((block, v))
            elif op.opname == 'gc_pop_roots':
                for v in op.args:
                    if not isinstance(v, Variable):
                        continue
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
    assert regalloc.graph is graph
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

def make_bitmask(filled, graph='?'):
    n = filled.count(False)
    if n == 0:
        return (None, None)
    bitmask = 0
    last_index = 0
    for i in range(len(filled)):
        if not filled[i]:
            bitmask <<= (i - last_index)
            last_index = i
            bitmask |= 1
    assert bitmask & 1
    if bitmask != intmask(bitmask):
        raise GCBitmaskTooLong("the graph %r is too complex: cannot create "
                               "a bitmask telling than more than 31/63 "
                               "shadowstack entries are unused" % (graph,))
    # the mask is always a positive value, but it is replaced by a
    # negative value during a minor collection root walking.  Then,
    # if the next minor collection finds an already-negative value,
    # we know we can stop.  So that's why we don't include here an
    # optimization to not re-write a same-valued mask: it is important
    # to re-write the value, to turn it from potentially negative back
    # to positive, in order to mark this shadow frame as modified.
    assert bitmask > 0
    return (last_index, bitmask)


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
        bitmask_index, bitmask = make_bitmask(filled, regalloc.graph)
        if bitmask_index is not None:
            # xxx we might in some cases avoid this gc_save_root
            # entirely, if we know we're after another gc_push/gc_pop
            # that wrote exactly the same mask at the same index
            bitmask_c = Constant(bitmask, lltype.Signed)
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
                args = [v for v in op.args if isinstance(v, Variable)]
                newops += expand_one_push_roots(regalloc, args)
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
                if isinstance(v, Variable) and regalloc.checkcolor(v, index):
                    break
            else:
                continue   # no variable goes into index i

            succ = set()
            pending_succ = [(block, v)]
            while pending_succ:
                block1, v1 = pending_succ.pop()
                assert regalloc.checkcolor(v1, index)
                for op1 in block1.operations:
                    if is_trivial_rewrite(op1) and op1.args[0] is v1:
                        if regalloc.checkcolor(op1.result, index):
                            pending_succ.append((block1, op1.result))
                for link1 in block1.exits:
                    for i2, v2 in enumerate(link1.args):
                        if v2 is not v1:
                            continue
                        block2 = link1.target
                        w2 = block2.inputargs[i2]
                        if w2 in succ or not regalloc.checkcolor(w2, index):
                            continue
                        succ.add(w2)
                        for op2 in block2.operations:
                            if op2.opname in ('gc_save_root', 'gc_pop_roots'):
                                break
                        else:
                            pending_succ.append((block2, w2))
            U.union_list(list(succ))
            S.update(succ)

        G = defaultdict(set)
        for block in graph.iterblocks():
            found = False
            for opindex, op in enumerate(block.operations):
                if op.opname == 'gc_save_root':
                    if (isinstance(op.args[1], Constant) and
                        op.args[1].concretetype == lltype.Signed):
                        break
                    elif op.args[0].value == index:
                        found = True
                        break
            if not found or not isinstance(op.args[1], Variable):
                continue   # no matching gc_save_root in this block

            key = (block, op)
            pred = set()
            pending_pred = [(block, op.args[1], opindex)]
            while pending_pred:
                block1, v1, opindex1 = pending_pred.pop()
                assert regalloc.getcolor(v1) == index
                for i in range(opindex1-1, -1, -1):
                    op1 = block1.operations[i]
                    if op1.opname == 'gc_pop_roots':
                        break    # stop
                    if op1.result is v1:
                        if not is_trivial_rewrite(op1):
                            break   # stop
                        if not regalloc.checkcolor(op1.args[0], index):
                            break   # stop
                        v1 = op1.args[0]
                else:
                    varindex = block1.inputargs.index(v1)
                    if v1 in pred:
                        continue    # already done
                    pred.add(v1)
                    for link1 in entrymap[block1]:
                        prevblock1 = link1.prevblock
                        if prevblock1 is not None:
                            w1 = link1.args[varindex]
                            if isinstance(w1, Variable) and w1 not in pred:
                                if regalloc.checkcolor(w1, index):
                                    pending_pred.append((prevblock1, w1,
                                                len(prevblock1.operations)))
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

    # Sort P so that it prefers places that would avoid multiple
    # gcsaveroots (smaller 'heuristic' result, so first in sorted
    # order); but also prefers smaller overall pieces, because it
    # might be possible to remove several small-scale pieces instead
    # of one big-scale one.
    def heuristic((index, P, gcsaveroots)):
        return float(len(P)) / len(gcsaveroots)
    Plist.sort(key=heuristic)

    variables_along_changes = {}
    live_at_start_of_block = set()   # set of (block, index)
    insert_gc_push_root = defaultdict(list)

    for index, P, gcsaveroots in Plist:
        # if this Plist entry is not valid any more because of changes
        # done by the previous entries, drop it
        if any((inputvars[v][0], index) in live_at_start_of_block for v in P):
            continue
        if any(op not in block.operations for block, op in gcsaveroots):
            continue
        for v in P:
            assert regalloc.getcolor(v) == index
            assert v not in variables_along_changes

        success_count = 0
        mark = []

        for v in P:
            block, varindex = inputvars[v]
            for link in entrymap[block]:
                w = link.args[varindex]
                if link.prevblock is not None:
                    prevoperations = link.prevblock.operations
                else:
                    prevoperations = []
                for op in reversed(prevoperations):
                    if op.opname == 'gc_pop_roots':
                        # it is possible to have gc_pop_roots() without
                        # w in the args, if w is the result of the call
                        # that comes just before.
                        if (isinstance(w, Variable) and
                                w in op.args and
                                regalloc.checkcolor(w, index)):
                            success_count += 1
                        else:
                            mark.append((index, link, varindex))
                        break
                    if op.result is w:
                        if is_trivial_rewrite(op) and (
                                regalloc.checkcolor(op.args[0], index)):
                            w = op.args[0]
                        else:
                            mark.append((index, link, varindex))
                            break
                else:
                    if not isinstance(w, Variable) or w not in P:
                        mark.append((index, link, varindex))

        if success_count > 0:
            for block, op in gcsaveroots:
                newops = list(block.operations)
                newops.remove(op)
                block.operations = newops
            for index, link, varindex in mark:
                insert_gc_push_root[link].append((index, link.args[varindex]))
            for v in P:
                block, varindex = inputvars[v]
                variables_along_changes[v] = block, index
                live_at_start_of_block.add((block, index))

    for link in insert_gc_push_root:
        newops = [_gc_save_root(index, v)
                  for index, v in sorted(insert_gc_push_root[link])]
        insert_empty_block(link, newops=newops)


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
                args = [v for v in op.args if isinstance(v, Variable)]
                expanded = list(expand_one_pop_roots(regalloc, args))
                drop = {}
                for op1 in expanded:
                    if isinstance(op1.args[1], Variable):
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


def add_leave_roots_frame(graph, regalloc):
    # put the 'gc_leave_roots_frame' operations as early as possible,
    # that is, just after the last 'gc_restore_root' reached.  This is
    # done by putting it along a link, such that the previous block
    # contains a 'gc_restore_root' and from the next block it is not
    # possible to reach any extra 'gc_restore_root'; then, as doing
    # this is not as precise as we'd like, we first break every block
    # just after their last 'gc_restore_root'.
    if regalloc is None:
        return

    # break blocks after their last 'gc_restore_root', unless they
    # are already at the last position
    for block in graph.iterblocks():
        ops = block.operations
        for i in range(len(ops)-1, -1, -1):
            if ops[i].opname == 'gc_restore_root':
                if i < len(ops) - 1:
                    split_block(block, i + 1)
                break
    # done

    entrymap = mkentrymap(graph)
    flagged_blocks = set()     # blocks with 'gc_restore_root' in them,
                               # or from which we can reach such a block
    for block in graph.iterblocks():
        for op in block.operations:
            if op.opname == 'gc_restore_root':
                flagged_blocks.add(block)
                break    # interrupt this block, go to the next one

    links = list(graph.iterlinks())
    links.reverse()

    while True:
        prev_length = len(flagged_blocks)
        for link in links:
            if link.target in flagged_blocks:
                flagged_blocks.add(link.prevblock)
        if len(flagged_blocks) == prev_length:
            break
    assert graph.returnblock not in flagged_blocks
    assert graph.startblock in flagged_blocks

    extra_blocks = {}
    for link in links:
        block = link.target
        if (link.prevblock in flagged_blocks and
                block not in flagged_blocks):
            # share the gc_leave_roots_frame if possible
            if block not in extra_blocks:
                newblock = Block([v.copy() for v in block.inputargs])
                newblock.operations.append(
                    SpaceOperation('gc_leave_roots_frame', [],
                                   varoftype(lltype.Void)))
                newblock.closeblock(Link(list(newblock.inputargs), block))
                extra_blocks[block] = newblock
            link.target = extra_blocks[block]

    # check all blocks not in flagged_blocks: they might contain a
    # gc_save_root() that writes the bitmask meaning "everything is
    # free".  Remove such gc_save_root().
    bitmask_all_free = (1 << regalloc.numcolors) - 1
    for block in graph.iterblocks():
        if block in flagged_blocks:
            continue
        newops = []
        for op in block.operations:
            if op.opname == 'gc_save_root':
                assert isinstance(op.args[1], Constant)
                assert op.args[1].value == bitmask_all_free
            else:
                newops.append(op)
        if len(newops) < len(block.operations):
            block.operations = newops


def add_enter_roots_frame(graph, regalloc, c_gcdata):
    if regalloc is None:
        return
    insert_empty_startblock(graph)
    c_num = Constant(regalloc.numcolors, lltype.Signed)
    graph.startblock.operations.append(
        SpaceOperation('gc_enter_roots_frame', [c_gcdata, c_num],
                       varoftype(lltype.Void)))

    join_blocks(graph)  # for the new block just above, but also for the extra
                        # new blocks made by insert_empty_block() earlier


class GCBitmaskTooLong(Exception):
    pass

class PostProcessCheckError(Exception):
    pass

def postprocess_double_check(graph, force_frame=False):
    # Debugging only: double-check that the placement is correct.
    # Assumes that every gc_restore_root() indicates that the variable
    # must be saved at the given position in the shadowstack frame (in
    # practice it may have moved because of the GC, but in theory it
    # is still the "same" object).  So we build the set of all known
    # valid-in-all-paths saved locations, and check that.

    saved = {}  # {var-from-inputargs: location} where location is:
                #    <unset>: we haven't seen this variable so far
                #    set-of-indexes: says where the variable is always
                #                    saved at the start of this block
                #    empty-set: same as above, so: "saved nowhere"

    left_frame = set()    # set of blocks, gc_leave_roots_frame was called
                          # before the start of this block

    for v in graph.startblock.inputargs:
        saved[v] = frozenset()    # function arguments are not saved anywhere

    if (len(graph.startblock.operations) == 0 or
            graph.startblock.operations[0].opname != 'gc_enter_roots_frame'):
        if not force_frame:
            left_frame.add(graph.startblock)    # no frame at all here

    pending = set([graph.startblock])
    while pending:
        block = pending.pop()
        locsaved = {}
        left = (block in left_frame)
        if not left:
            for v in block.inputargs:
                locsaved[v] = saved[v]
        for op in block.operations:
            if op.opname == 'gc_restore_root':
                if left:
                    raise PostProcessCheckError(graph, block, op, 'left!')
                if isinstance(op.args[1], Constant):
                    continue
                num = op.args[0].value
                if num not in locsaved[op.args[1]]:
                    raise PostProcessCheckError(graph, block, op, num, locsaved)
            elif op.opname == 'gc_save_root':
                if left:
                    raise PostProcessCheckError(graph, block, op, 'left!')
                num = op.args[0].value
                # first, cancel any other variable that would be saved in 'num'
                for v in locsaved:
                    locsaved[v] = locsaved[v].difference([num])
                #
                v = op.args[1]
                if isinstance(v, Variable):
                    locsaved[v] = locsaved[v].union([num])
                else:
                    if v.concretetype != lltype.Signed:
                        locsaved[v] = locsaved.get(v, frozenset()).union([num])
                        continue
                    bitmask = v.value
                    if bitmask != 1:
                        # cancel any variable that would be saved in any
                        # position shown by the bitmask, not just 'num'
                        assert bitmask & 1
                        assert 1 < bitmask < (2<<num)
                        nummask = [i for i in range(num+1)
                                     if bitmask & (1<<(num-i))]
                        assert nummask[-1] == num
                        for v in locsaved:
                            locsaved[v] = locsaved[v].difference(nummask)
            elif op.opname == 'gc_leave_roots_frame':
                if left:
                    raise PostProcessCheckError(graph, block, op, 'left!')
                left = True
            elif is_trivial_rewrite(op) and not left:
                locsaved[op.result] = locsaved[op.args[0]]
            else:
                locsaved[op.result] = frozenset()
        for link in block.exits:
            changed = False
            if left:
                if link.target not in left_frame:
                    left_frame.add(link.target)
                    changed = True
            else:
                for i, v in enumerate(link.args):
                    try:
                        loc = locsaved[v]
                    except KeyError:
                        assert isinstance(v, Constant)
                        loc = frozenset()
                    w = link.target.inputargs[i]
                    if w in saved:
                        if loc == saved[w]:
                            continue      # already up-to-date
                        loc = loc.intersection(saved[w])
                    saved[w] = loc
                    changed = True
            if changed:
                pending.add(link.target)

    assert graph.getreturnvar() not in saved   # missing gc_leave_roots_frame?


def postprocess_graph(graph, c_gcdata):
    """Collect information about the gc_push_roots and gc_pop_roots
    added in this complete graph, and replace them with real operations.
    """
    regalloc = allocate_registers(graph)
    expand_push_roots(graph, regalloc)
    move_pushes_earlier(graph, regalloc)
    expand_pop_roots(graph, regalloc)
    add_leave_roots_frame(graph, regalloc)
    add_enter_roots_frame(graph, regalloc, c_gcdata)
    checkgraph(graph)
    postprocess_double_check(graph)
    return (regalloc is not None)


def postprocess_inlining(graph):
    """We first write calls to GC functions with gc_push_roots(...) and
    gc_pop_roots(...) around.  Then we inline some of these functions.
    As a result, the gc_push_roots and gc_pop_roots are no longer in
    the same block.  Fix that by moving the gc_push_roots/gc_pop_roots
    inside the inlined portion of the graph, around every call.

    We could also get a correct result by doing things in a different
    order, e.g. first postprocess_graph() and then inlining.  However,
    this order brings an important benefit: if the inlined graph has a
    fast-path, like malloc_fixedsize(), then there are no gc_push_roots
    and gc_pop_roots left along the fast-path.
    """
    for block in graph.iterblocks():
        for i in range(len(block.operations)-1, -1, -1):
            op = block.operations[i]
            if op.opname == 'gc_pop_roots':
                break
            if op.opname == 'gc_push_roots':
                _fix_graph_after_inlining(graph, block, i)
                break

def _fix_graph_after_inlining(graph, initial_block, initial_index):
    op = initial_block.operations.pop(initial_index)
    assert op.opname == 'gc_push_roots'
    seen = set()
    pending = [(initial_block, initial_index, op.args)]
    while pending:
        block, start_index, track_args = pending.pop()
        if block in seen:
            continue
        seen.add(block)
        assert block.operations != ()     # did not find the gc_pop_roots?
        new_operations = block.operations[:start_index]
        stop = False
        for i in range(start_index, len(block.operations)):
            op = block.operations[i]
            if op.opname == 'gc_push_roots':
                raise Exception("%r: seems to have inlined another graph "
                                "which also uses GC roots" % (graph,))
            if op.opname == 'gc_pop_roots':
                # end of the inlined graph, drop gc_pop_roots, keep the tail
                new_operations += block.operations[i + 1:]
                stop = True
                break
            if op.opname in ('direct_call', 'indirect_call'):
                new_operations.append(SpaceOperation('gc_push_roots',
                                                     track_args[:],
                                                     varoftype(lltype.Void)))
                new_operations.append(op)
                new_operations.append(SpaceOperation('gc_pop_roots',
                                                     track_args[:],
                                                     varoftype(lltype.Void)))
            else:
                new_operations.append(op)
        block.operations = new_operations
        if not stop:
            for link in block.exits:
                track_next = []
                for v in track_args:
                    i = link.args.index(v)   # should really be here
                    w = link.target.inputargs[i]
                    track_next.append(w)
                pending.append((link.target, 0, track_next))
