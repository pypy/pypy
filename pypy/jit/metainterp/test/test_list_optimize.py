
import py
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.metainterp.optimize import (PerfectSpecializer,
    CancelInefficientLoop, VirtualInstanceSpecNode, FixedClassSpecNode,
    rebuild_boxes_from_guard_failure, AllocationStorage,
    NotSpecNode, FixedList)
from pypy.jit.metainterp.history import BoxInt, BoxPtr, ConstInt
from pypy.jit.metainterp.test.test_optimize import Loop, equaloplists, cpu
from pypy.jit.metainterp.specnode import DelayedFixedListSpecNode

# delayed list tests

class A:
    TP = lltype.GcArray(lltype.Signed)
    lst = lltype.malloc(TP, 3)
    l = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lst))
    e0 = BoxInt(0)
    e1 = BoxInt(0)
    ad = cpu.arraydescrof(TP)
    ops = [
        ResOperation(rop.MERGE_POINT, [l], None),
        ResOperation(rop.GETARRAYITEM_GC, [l, ConstInt(0)], e0, ad),
        ResOperation(rop.SETARRAYITEM_GC, [l, ConstInt(0), e0], None, ad),
        ResOperation(rop.GETARRAYITEM_GC, [l, ConstInt(0)], e1, ad),
        ResOperation(rop.SETARRAYITEM_GC, [l, ConstInt(0), e1], None, ad),
        ResOperation(rop.JUMP, [l], None),
        ]

def test_A_find_nodes():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    node = spec.nodes[A.l]
    assert isinstance(node.cls.source, FixedList)
    assert node.expanded_fields.keys() == [ConstInt(0)]

def test_A_intersect():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert isinstance(spec.specnodes[0], DelayedFixedListSpecNode)

def test_A_optimize_loop():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation(rop.MERGE_POINT, [A.l, A.e0], None),
        ResOperation(rop.SETARRAYITEM_GC, [A.l, ConstInt(0), A.e0], None, A.ad),
        ResOperation(rop.JUMP, [A.l, A.e0], None)
    ])

# ----------------------------------------------------------------------------

class B:
    locals().update(A.__dict__)
    e2 = BoxInt(0)
    e3 = BoxInt(0)
    ops = [
        ResOperation(rop.MERGE_POINT, [l], None),
        ResOperation(rop.GETARRAYITEM_GC, [l, ConstInt(0)], e0, ad),
        ResOperation(rop.INT_ADD, [e0, ConstInt(1)], e1),
        ResOperation(rop.SETARRAYITEM_GC, [l, ConstInt(0), e1], None, ad),
        ResOperation(-123, [e1], None),
        ResOperation(rop.GETARRAYITEM_GC, [l, ConstInt(0)], e2, ad),
        ResOperation(rop.INT_ADD, [e2, ConstInt(1)], e3),
        ResOperation(rop.SETARRAYITEM_GC, [l, ConstInt(0), e3], None, ad),
        ResOperation(rop.JUMP, [l], None),
    ]

def test_B_optimize_loop():
    spec = PerfectSpecializer(Loop(B.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation(rop.MERGE_POINT, [B.l, B.e0], None),
        ResOperation(rop.INT_ADD, [B.e0, ConstInt(1)], B.e1),
        ResOperation(rop.SETARRAYITEM_GC, [B.l, ConstInt(0), B.e1], None, B.ad),
        ResOperation(-123, [B.e1], None),
        ResOperation(rop.GETARRAYITEM_GC, [B.l, ConstInt(0)], B.e2, B.ad),
        ResOperation(rop.INT_ADD, [B.e2, ConstInt(1)], B.e3),
        ResOperation(rop.SETARRAYITEM_GC, [B.l, ConstInt(0), B.e3], None, B.ad),
        ResOperation(rop.JUMP, [B.l, B.e3], None),
    ])

# ----------------------------------------------------------------------------

class C:
    locals().update(A.__dict__)
    e3 = BoxInt(0)
    e2 = BoxInt(0)
    ops = [
        ResOperation(rop.MERGE_POINT, [l], None),
        ResOperation(rop.GETARRAYITEM_GC, [l, ConstInt(0)], e0, ad),
        ResOperation(rop.INT_ADD, [e0, ConstInt(1)], e1),
        ResOperation(rop.SETARRAYITEM_GC, [l, ConstInt(0), e1], None, ad),
        ResOperation(-123, [e1], None),
        ResOperation(rop.GETARRAYITEM_GC, [l, ConstInt(0)], e2, ad),
        ResOperation(rop.INT_ADD, [e2, ConstInt(1)], e3),
        ResOperation(rop.SETARRAYITEM_GC, [l, ConstInt(0), e3], None, ad),
        ResOperation(rop.JUMP, [l], None),
    ]
    
def test_C_optimize_loop():
    py.test.skip("XXX")
    xxx
