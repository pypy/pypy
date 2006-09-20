from pypy.translator.unsimplify import varoftype
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.support import \
     needs_conservative_livevar_calculation, split_block_with_keepalive, \
     find_loop_blocks, find_backedges, compute_reachability

from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model

NonGcB = lltype.Struct("B", ('x', lltype.Signed))
GcA = lltype.GcStruct("A", ('b', NonGcB), ('c', lltype.Ptr(lltype.FuncType([], lltype.Void))))

def test_nclc_should_be_true():
    # this is testing a block like:
    # +--- inputargs: pointer_to_gc
    # | v0 <- op_getsubstruct pointer_to_gc 'b'
    # +--- exitargs: v0 (i.e. pointer to non-gc)
    llops = LowLevelOpList()
    ptr_a = varoftype(lltype.Ptr(GcA))
    v_res = llops.genop("getsubstruct", [ptr_a, model.Constant('b', lltype.Void)],
                        resulttype=lltype.Ptr(NonGcB))
    block = model.Block([ptr_a])
    block.operations.extend(llops)
    block.closeblock(model.Link([v_res], None))
    assert needs_conservative_livevar_calculation(block)

def test_nclc_nongc_not_passed_on():
    # +--- inputargs: pointer_to_gc
    # | v0 <- op_getsubstruct pointer_to_gc 'b'
    # +--- exitargs: pointer_to_gc (i.e. the pointer to non-gc doesn't leave the block)
    llops = LowLevelOpList()
    ptr_a = varoftype(lltype.Ptr(GcA))
    v_res = llops.genop("getsubstruct", [ptr_a, model.Constant('b', lltype.Void)],
                        resulttype=lltype.Ptr(NonGcB))
    block = model.Block([ptr_a])
    block.operations.extend(llops)
    block.closeblock(model.Link([ptr_a], None))
    assert not needs_conservative_livevar_calculation(block)

def test_nclc_ignore_functype():
    # +--- inputargs: pointer_to_gc
    # | v0 <- op_getfield pointer_to_gc 'c'
    # +--- exitargs: v0 (i.e. a pointer to function)
    # pointers to functions are 'not gc' but functions are also
    # immortal so you don't need to muck around inserting keepalives
    # so *they* don't die!
    llops = LowLevelOpList()
    ptr_a = varoftype(lltype.Ptr(GcA))
    v_res = llops.genop("getfield", [ptr_a, model.Constant('c', lltype.Void)],
                        resulttype=GcA.c)
    block = model.Block([ptr_a])
    block.operations.extend(llops)
    block.closeblock(model.Link([v_res], None))
    assert not needs_conservative_livevar_calculation(block)

def test_sbwk_should_insert_keepalives():
    # this is testing something like:
    # v0 <- op_producing_non_gc
    # v1 <- op_using_v0        <- split here
    llops = LowLevelOpList()
    ptr_a = varoftype(lltype.Ptr(GcA))
    v_res = llops.genop("getfield", [ptr_a, model.Constant('b', lltype.Void)],
                        resulttype=lltype.Ptr(NonGcB))
    llops.genop("direct_call", [model.Constant(None, lltype.Void), v_res],
                resulttype=lltype.Void)
    block = model.Block([ptr_a])
    block.operations.extend(llops)
    block.closeblock(model.Link([], None))
    link = split_block_with_keepalive(block, 1)
    assert 'keepalive' in [op.opname for op in link.target.operations]

def test_sbwk_should_insert_keepalives_2():
    # this is testing something like:
    # v0 <- op_producing_non_gc
    # v1 <- op_not_using_v0        <- split here
    # v2 <- op_using_v0
    llops = LowLevelOpList()
    ptr_a = varoftype(lltype.Ptr(GcA))
    v_res = llops.genop("getfield", [ptr_a, model.Constant('b', lltype.Void)],
                        resulttype=lltype.Ptr(NonGcB))
    llops.genop("direct_call", [model.Constant(None, lltype.Void)],
                resulttype=lltype.Void)
    llops.genop("direct_call", [model.Constant(None, lltype.Void), v_res],
                resulttype=lltype.Void)
    block = model.Block([ptr_a])
    block.operations.extend(llops)
    block.closeblock(model.Link([], None))
    link = split_block_with_keepalive(block, 1)
    assert 'keepalive' in [op.opname for op in link.target.operations]

#__________________________________________________________
# test compute_reachability

def test_simple_compute_reachability():
    def f(x):
        if x < 0:
            if x == -1:
                return x+1
            else:
                return x+2
        else:
            if x == 1:
                return x-1
            else:
                return x-2
    t = TranslationContext()
    g = t.buildflowgraph(f)
    reach = compute_reachability(g)
    assert len(reach[g.startblock]) == 7
    assert len(reach[g.startblock.exits[0].target]) == 3
    assert len(reach[g.startblock.exits[1].target]) == 3
#__________________________________________________________
# test loop detection

def test_find_backedges():
    def f(k):
        result = 0
        for i in range(k):
            result += 1
        for j in range(k):
            result += 1
        return result
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backedges = find_backedges(graph)
    assert len(backedges) == 2

def test_find_loop_blocks():
    def f(k):
        result = 0
        for i in range(k):
            result += 1
        for j in range(k):
            result += 1
        return result
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    loop_blocks = find_loop_blocks(graph)
    assert len(loop_blocks) == 4

def test_find_loop_blocks_simple():
    def f(a):
        if a <= 0:
            return 1
        return f(a - 1)
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backedges = find_backedges(graph)
    assert backedges == []
    loop_blocks = find_loop_blocks(graph)
    assert len(loop_blocks) == 0

def test_find_loop_blocks2():
    class A:
        pass
    def f(n):
        a1 = A()
        a1.x = 1
        a2 = A()
        a2.x = 2
        if n > 0:
            a = a1
        else:
            a = a2
        return a.x
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backedges = find_backedges(graph)
    assert backedges == []
    loop_blocks = find_loop_blocks(graph)
    assert len(loop_blocks) == 0

def test_find_loop_blocks3():
    import os
    def ps(loops):
        return 42.0, 42.1
    def f(loops):
        benchtime, stones = ps(abs(loops))
        s = '' # annotator happiness
        if loops >= 0:
            s = ("RPystone(%s) time for %d passes = %f" %
                 (23, loops, benchtime) + '\n' + (
                 "This machine benchmarks at %f pystones/second" % stones))
        os.write(1, s)
        if loops == 12345:
            f(loops-1)
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    graph = graphof(t, f)
    backedges = find_backedges(graph)
    assert backedges == []
    loop_blocks = find_loop_blocks(graph)
    assert len(loop_blocks) == 0

