from pypy.translator.backendopt.support import \
     needs_conservative_livevar_calculation, split_block_with_keepalive

from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model

NonGcB = lltype.Struct("B", ('x', lltype.Signed))
GcA = lltype.GcStruct("A", ('b', NonGcB), ('c', lltype.Ptr(lltype.FuncType([], lltype.Void))))

def varoftype(concretetype):
    var = model.Variable()
    var.concretetype = concretetype
    return var

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


