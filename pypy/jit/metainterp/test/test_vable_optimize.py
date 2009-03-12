import py

from pypy.rpython.lltypesystem import lltype, rclass, llmemory
from pypy.rpython.lltypesystem.rvirtualizable2 import VABLERTIPTR
from pypy.rpython.lltypesystem.rvirtualizable2 import VirtualizableAccessor
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import heaptracker
from pypy.jit.metainterp.history import ConstInt, ConstAddr, BoxInt, BoxPtr
from pypy.jit.metainterp.optimize import (PerfectSpecializer,
                                          VirtualizableSpecNode,
                                          VirtualInstanceSpecNode,
                                          NotSpecNode,
                                          DelayedSpecNode)
from pypy.jit.metainterp.virtualizable import VirtualizableDesc
from pypy.jit.metainterp.test.test_optimize import (cpu, NODE, node_vtable,
                                                    equaloplists, Loop,
                                                    ResOperation)
#from pypy.jit.metainterp.codewriter import ListDescr

# ____________________________________________________________

XY = lltype.GcStruct(
    'XY',
    ('parent', rclass.OBJECT),
    ('vable_base', llmemory.Address),
    ('vable_rti', VABLERTIPTR),
    ('x', lltype.Signed),
    ('l', lltype.Ptr(lltype.GcArray(lltype.Signed))),
    ('node', lltype.Ptr(NODE)),
    hints = {'virtualizable2': True,
             'virtuals':()},
    adtmeths = {'access': VirtualizableAccessor()})
XY._adtmeths['access'].initialize(XY, ['x', 'node', 'l'])

xy_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
xy_vtable.name = lltype.malloc(rclass.OBJECT_VTABLE.name.TO, 3, immortal=True)
xy_vtable.name[0] = 'X'
xy_vtable.name[1] = 'Y'
xy_vtable.name[2] = '\x00'
heaptracker.set_testing_vtable_for_gcstruct(XY, xy_vtable)

XYSUB = lltype.GcStruct(
    'XYSUB',
    ('parent', XY),
    ('z', lltype.Signed),
    hints = {'virtualizable2': True},
    adtmeths = {'access': VirtualizableAccessor()})
XYSUB._adtmeths['access'].initialize(XYSUB, ['z'], PARENT=XY)

xysub_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
xysub_vtable.name = lltype.malloc(rclass.OBJECT_VTABLE.name.TO, 6,
                                  immortal=True)
xysub_vtable.name[0] = 'X'
xysub_vtable.name[1] = 'Y'
xysub_vtable.name[2] = 'S'
xysub_vtable.name[3] = 'U'
xysub_vtable.name[4] = 'B'
xysub_vtable.name[5] = '\x00'
heaptracker.set_testing_vtable_for_gcstruct(XYSUB, xysub_vtable)

# ____________________________________________________________

xy_desc = VirtualizableDesc(cpu, XY, XY)

# ____________________________________________________________

class A:
    ofs_node = runner.CPU.fielddescrof(XY, 'node')
    ofs_l = runner.CPU.fielddescrof(XY, 'l')
    ofs_value = runner.CPU.fielddescrof(NODE, 'value')
    size_of_node = runner.CPU.sizeof(NODE)
    #
    frame = lltype.malloc(XY)
    frame.vable_rti = lltype.nullptr(XY.vable_rti.TO)
    frame.node = lltype.malloc(NODE)
    frame.node.value = 20
    sum = BoxInt(0)
    fr = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame))
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.node))
    nextnode = lltype.malloc(NODE)
    nextnode.value = 19
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    v = BoxInt(frame.node.value)
    v2 = BoxInt(nextnode.value)
    sum2 = BoxInt(0 + frame.node.value)
    ops = [
        ResOperation('merge_point', [sum, fr], None),
        ResOperation('guard_nonvirtualized', [fr, ConstAddr(xy_vtable, cpu)],
                     None, ofs_node),
        ResOperation('getfield_gc', [fr], n1, ofs_node),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('setfield_gc', [fr, n2], None, ofs_node),
        ResOperation('jump', [sum2, fr], None),
        ]
    ops[1].vdesc = xy_desc

def test_A_find_nodes():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    assert spec.nodes[A.fr].virtualized

def test_A_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[A.fr].escaped
    assert spec.nodes[A.fr].virtualized
    assert not spec.nodes[A.n1].escaped
    assert not spec.nodes[A.n2].escaped
    assert isinstance(spec.specnodes[1], VirtualizableSpecNode)

def test_A_optimize_loop():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop(None)
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [A.sum, A.fr, A.v], None),
        ResOperation('int_sub', [A.v, ConstInt(1)], A.v2),
        ResOperation('int_add', [A.sum, A.v], A.sum2),
        ResOperation('jump', [A.sum2, A.fr, A.v2], None),
    ])

# ____________________________________________________________

class B:
    ofs_node = runner.CPU.fielddescrof(XY, 'node')
    ofs_value = runner.CPU.fielddescrof(NODE, 'value')
    size_of_node = runner.CPU.sizeof(NODE)
    #
    frame = lltype.malloc(XY)
    frame.vable_rti = lltype.nullptr(XY.vable_rti.TO)
    frame.node = lltype.malloc(NODE)
    frame.node.value = 20
    fr = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame))
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.node))
    v = BoxInt(13)
    ops = [
        ResOperation('merge_point', [fr], None),
        ResOperation('guard_nonvirtualized', [fr, ConstAddr(xy_vtable, cpu)],
                     None, ofs_node),
        ResOperation('getfield_gc', [fr], n1, ofs_node),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('jump', [fr], None),
        ]
    ops[1].vdesc = xy_desc

def test_B_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(B.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[B.fr].escaped
    assert spec.nodes[B.fr].virtualized
    assert spec.nodes[B.n1].escaped
    assert isinstance(spec.specnodes[0], VirtualizableSpecNode)
    assert len(spec.specnodes[0].fields) == 1
    assert spec.specnodes[0].fields[0][0] == B.ofs_node
    assert isinstance(spec.specnodes[0].fields[0][1], NotSpecNode)

# ____________________________________________________________

class C:
    locals().update(B.__dict__)
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.node))
    v2 = BoxInt(13)
    ops = [
        ResOperation('merge_point', [fr], None),
        ResOperation('guard_nonvirtualized', [fr, ConstAddr(xy_vtable, cpu)],
                     None, ofs_node),
        #
        ResOperation('getfield_gc', [fr], n1, ofs_node),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        #
        ResOperation('getfield_gc', [fr], n2, ofs_node),
        ResOperation('guard_class', [n2, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n2], v2, ofs_value),
        #
        ResOperation('jump', [fr], None),
        ]
    ops[1].vdesc = xy_desc

def test_C_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(C.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[C.fr].escaped
    assert spec.nodes[C.fr].virtualized
    assert spec.nodes[C.n1].escaped
    assert spec.nodes[C.n2].escaped
    assert isinstance(spec.specnodes[0], VirtualizableSpecNode)
    assert len(spec.specnodes[0].fields) == 1
    assert spec.specnodes[0].fields[0][0] == C.ofs_node
    assert isinstance(spec.specnodes[0].fields[0][1], DelayedSpecNode)


# ____________________________________________________________

if 0:
  class D:
    class SomeDescr(ListDescr):
        def __init__(self):
            pass
    
    locals().update(A.__dict__)
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.node))
    v2 = BoxInt(13)
    l = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.node))
    ops = [
        ResOperation('merge_point', [fr], None),
        ResOperation('guard_nonvirtualized', [fr, ConstAddr(xy_vtable, cpu),
                                              ConstInt(ofs_node)], None),
        #
        ResOperation('getfield_gc', [fr, ConstInt(ofs_l)], l),
        ResOperation('guard_builtin', [l, SomeDescr()], None),
        ResOperation('getitem', [None, l, ConstInt(0)], v2),
        ResOperation('setitem', [None, l, ConstInt(0), v2], None),
        ResOperation('jump', [fr], None),
        ]
    ops[1].vdesc = xy_desc

def test_D_intersect_input_and_output():
    py.test.skip("XXX")
    spec = PerfectSpecializer(Loop(D.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[D.fr].escaped
    assert spec.nodes[D.fr].virtualized
    assert not spec.nodes[D.l].escaped
    assert spec.nodes[D.l].expanded_fields.keys() == [0]
