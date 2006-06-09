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
    llops = LowLevelOpList()
    ptr_a = varoftype(lltype.Ptr(GcA))
    v_res = llops.genop("getfield", [ptr_a, model.Constant('b', lltype.Void)],
                        resulttype=lltype.Ptr(NonGcB))
    block = model.Block([ptr_a])
    block.operations.extend(llops)
    block.closeblock(model.Link([v_res], None))
    assert needs_conservative_livevar_calculation(block)

def test_nclc_nongc_not_passed_on():
    llops = LowLevelOpList()
    ptr_a = varoftype(lltype.Ptr(GcA))
    v_res = llops.genop("getfield", [ptr_a, model.Constant('b', lltype.Void)],
                        resulttype=lltype.Ptr(NonGcB))
    block = model.Block([ptr_a])
    block.operations.extend(llops)
    block.closeblock(model.Link([ptr_a], None))
    assert not needs_conservative_livevar_calculation(block)

def test_nclc_ignore_functype():
    llops = LowLevelOpList()
    ptr_a = varoftype(lltype.Ptr(GcA))
    v_res = llops.genop("getfield", [ptr_a, model.Constant('c', lltype.Void)],
                        resulttype=GcA.c)
    block = model.Block([ptr_a])
    block.operations.extend(llops)
    block.closeblock(model.Link([v_res], None))
    assert not needs_conservative_livevar_calculation(block)

def test_sbwk_should_insert_keepalives():
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
    
