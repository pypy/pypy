import py
py.test.skip("redo me")

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
                                          FixedClassSpecNode)
#                                          DelayedSpecNode)
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
    ('inst_x', lltype.Signed),
    ('inst_l', lltype.Ptr(lltype.GcArray(lltype.Signed))),
    ('inst_node', lltype.Ptr(NODE)),
    hints = {'virtualizable2': True,
             'virtuals':()},
    adtmeths = {'access': VirtualizableAccessor()})
XY._adtmeths['access'].initialize(XY, ['inst_x', 'inst_node', 'inst_l'])

xy_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
heaptracker.set_testing_vtable_for_gcstruct(XY, xy_vtable, 'XY')

XYSUB = lltype.GcStruct(
    'XYSUB',
    ('parent', XY),
    ('z', lltype.Signed),
    hints = {'virtualizable2': True},
    adtmeths = {'access': VirtualizableAccessor()})
XYSUB._adtmeths['access'].initialize(XYSUB, ['z'], PARENT=XY)

xysub_vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
heaptracker.set_testing_vtable_for_gcstruct(XYSUB, xysub_vtable, 'XYSUB')

# ____________________________________________________________

xy_desc = VirtualizableDesc(cpu, XY, XY)

# ____________________________________________________________

class A:
    ofs_node = runner.LLtypeCPU.fielddescrof(XY, 'inst_node')
    ofs_l = runner.LLtypeCPU.fielddescrof(XY, 'inst_l')
    ofs_value = runner.LLtypeCPU.fielddescrof(NODE, 'value')
    size_of_node = runner.LLtypeCPU.sizeof(NODE)
    #
    frame = lltype.malloc(XY)
    frame.vable_rti = lltype.nullptr(XY.vable_rti.TO)
    frame.inst_node = lltype.malloc(NODE)
    frame.inst_node.value = 20
    sum = BoxInt(0)
    fr = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame))
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.inst_node))
    nextnode = lltype.malloc(NODE)
    nextnode.value = 19
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    v = BoxInt(frame.inst_node.value)
    v2 = BoxInt(nextnode.value)
    sum2 = BoxInt(0 + frame.inst_node.value)
    inputargs = [sum, fr]
    ops = [
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
    ops[0].vdesc = xy_desc

def test_A_find_nodes():
    spec = PerfectSpecializer(Loop(A.inputargs, A.ops))
    spec.find_nodes()
    assert spec.nodes[A.fr].virtualized

def test_A_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(A.inputargs, A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[A.fr].escaped
    assert spec.nodes[A.fr].virtualized
    assert not spec.nodes[A.n1].escaped
    assert not spec.nodes[A.n2].escaped
    assert isinstance(spec.specnodes[1], VirtualizableSpecNode)

def test_A_optimize_loop():
    spec = PerfectSpecializer(Loop(A.inputargs, A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [A.sum, A.fr, A.v]
    equaloplists(spec.loop.operations, [
        ResOperation('int_sub', [A.v, ConstInt(1)], A.v2),
        ResOperation('int_add', [A.sum, A.v], A.sum2),
        ResOperation('jump', [A.sum2, A.fr, A.v2], None),
    ])

# ____________________________________________________________

class B:
    ofs_node = runner.LLtypeCPU.fielddescrof(XY, 'inst_node')
    ofs_value = runner.LLtypeCPU.fielddescrof(NODE, 'value')
    size_of_node = runner.LLtypeCPU.sizeof(NODE)
    #
    frame = lltype.malloc(XY)
    frame.vable_rti = lltype.nullptr(XY.vable_rti.TO)
    frame.inst_node = lltype.malloc(NODE)
    frame.inst_node.value = 20
    fr = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame))
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.inst_node))
    v = BoxInt(13)
    inputargs = [fr]
    ops = [
        ResOperation('guard_nonvirtualized', [fr, ConstAddr(xy_vtable, cpu)],
                     None, ofs_node),
        ResOperation('getfield_gc', [fr], n1, ofs_node),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('jump', [fr], None),
        ]
    ops[0].vdesc = xy_desc

def test_B_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(B.inputargs, B.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[B.fr].escaped
    assert spec.nodes[B.fr].virtualized
    assert spec.nodes[B.n1].escaped
    assert isinstance(spec.specnodes[0], VirtualizableSpecNode)
    assert len(spec.specnodes[0].fields) == 3
    assert spec.specnodes[0].fields[2][0] == B.ofs_node
    assert isinstance(spec.specnodes[0].fields[2][1], NotSpecNode)

# ____________________________________________________________

class C:
    locals().update(B.__dict__)
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, frame.inst_node))
    v2 = BoxInt(13)
    inputargs = [fr]
    ops = [
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
    ops[0].vdesc = xy_desc

def test_C_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(C.inputargs, C.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[C.fr].escaped
    assert spec.nodes[C.fr].virtualized
    assert spec.nodes[C.n1].escaped
    assert spec.nodes[C.n2].escaped
    assert isinstance(spec.specnodes[0], VirtualizableSpecNode)
    assert len(spec.specnodes[0].fields) == 3
    assert spec.specnodes[0].fields[2][0] == C.ofs_node
    assert isinstance(spec.specnodes[0].fields[2][1], FixedClassSpecNode)


# ____________________________________________________________

class E:
    locals().update(A.__dict__)
    inputargs = [fr]
    ops = [
        ResOperation('guard_nonvirtualized', [fr, ConstAddr(xy_vtable, cpu)],
                     None, ofs_node),
        ResOperation('getfield_gc', [fr], n1, ofs_node),
        ResOperation('escape', [n1], None),
        ResOperation('getfield_gc', [fr], n2, ofs_node),
        ResOperation('escape', [n2], None),
        ResOperation('jump', [fr], None),
        ]
    ops[0].vdesc = xy_desc

def test_E_optimize_loop():
    spec = PerfectSpecializer(Loop(E.inputargs, E.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [E.fr, E.n1]
    equaloplists(spec.loop.operations, [
        ResOperation('escape', [E.n1], None),
        ResOperation('escape', [E.n1], None),
        ResOperation('jump', [E.fr, E.n1], None),
    ])
