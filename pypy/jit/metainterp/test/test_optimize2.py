
import py
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.history import ConstAddr, BoxPtr, TreeLoop,\
     ConstInt, BoxInt
from pypy.jit.backend.llgraph import runner

from pypy.jit.metainterp.optimize2 import optimize_loop
from pypy.jit.metainterp.test.test_optimize import equaloplists, ANY

node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
node_vtable_adr = llmemory.cast_ptr_to_adr(node_vtable)
cpu = runner.LLtypeCPU(None)
vtable_box = ConstAddr(node_vtable_adr, cpu)

NODE = lltype.GcForwardReference()
NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                    ('value', lltype.Signed),
                                    ('next', lltype.Ptr(NODE))))
node = lltype.malloc(NODE)
nodebox = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node))
nodedescr = cpu.fielddescrof(NODE, 'value')

def newloop(inputargs, operations):
    loop = TreeLoop("test")
    loop.inputargs = inputargs
    loop.operations = operations
    return loop

def test_remove_guard_class():
    ops = [
        ResOperation(rop.GUARD_CLASS, [nodebox, vtable_box], None),
        ResOperation(rop.GUARD_CLASS, [nodebox, vtable_box], None),
    ]
    ops[0].suboperations = [ResOperation(rop.FAIL, [], None)]
    ops[1].suboperations = [ResOperation(rop.FAIL, [], None)]
    loop = newloop([nodebox], ops)
    optimize_loop(None, [], loop)
    assert len(loop.operations) == 1

def test_remove_consecutive_guard_value_constfold():
    n = BoxInt(0)
    n1 = BoxInt(1)
    n2 = BoxInt(3)
    ops = [
        ResOperation(rop.GUARD_VALUE, [n, ConstInt(0)], None),
        ResOperation(rop.INT_ADD, [n, ConstInt(1)], n1),
        ResOperation(rop.GUARD_VALUE, [n1, ConstInt(1)], None),
        ResOperation(rop.INT_ADD, [n1, ConstInt(2)], n2),
    ]
    ops[0].suboperations = [ResOperation(rop.FAIL, [], None)]
    ops[2].suboperations = [ResOperation(rop.FAIL, [], None)]
    loop = newloop([n], ops)
    optimize_loop(None, [], loop)
    equaloplists(loop.operations, [
        ResOperation(rop.GUARD_VALUE, [n, ConstInt(0)], None),
        ])

def test_remove_consecutive_getfields():
    n1 = BoxInt()
    n2 = BoxInt()
    n3 = BoxInt()
    ops = [
        ResOperation(rop.GETFIELD_GC, [nodebox], n1, nodedescr),
        ResOperation(rop.GETFIELD_GC, [nodebox], n2, nodedescr),
        ResOperation(rop.INT_ADD, [n1, n2], n3),
    ]
    loop = newloop([nodebox], ops)
    optimize_loop(None, [], loop)
    equaloplists(loop.operations, [
        ResOperation(rop.GETFIELD_GC, [nodebox], n1, nodedescr),
        ResOperation(rop.INT_ADD, [n1, n1], n3),
        ])
    
def test_setfield_getfield_clean_cache():
    n1 = BoxInt()
    n2 = BoxInt()
    n3 = BoxInt()
    ops = [
        ResOperation(rop.GETFIELD_GC, [nodebox], n1, nodedescr),
        ResOperation(rop.SETFIELD_GC, [nodebox, ConstInt(3)], None, nodedescr),
        ResOperation(rop.GETFIELD_GC, [nodebox], n2, nodedescr),
        ResOperation(rop.CALL, [n2], None),
    ]
    loop = newloop([nodebox], ops)
    optimize_loop(None, [], loop)
    equaloplists(loop.operations, [
        ResOperation(rop.GETFIELD_GC, [nodebox], n1, nodedescr),
        ResOperation(rop.SETFIELD_GC, [nodebox, ConstInt(3)], None, nodedescr),
        ResOperation(rop.CALL, [ConstInt(3)], None),
        ])

