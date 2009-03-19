import py
import copy

from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import resoperation
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         ConstAddr)
from pypy.jit.metainterp.optimize import (PerfectSpecializer,
    CancelInefficientLoop, VirtualInstanceSpecNode, FixedClassSpecNode,
    rebuild_boxes_from_guard_failure, NotSpecNode)

cpu = runner.CPU(None)

NODE = lltype.GcForwardReference()
NODE.become(lltype.GcStruct('NODE', ('parent', OBJECT),
                                    ('value', lltype.Signed),
                                    ('next', lltype.Ptr(NODE))))

node_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
node_vtable_adr = llmemory.cast_ptr_to_adr(node_vtable)

NODE2 = lltype.GcStruct('NODE2', ('parent', NODE),
                                 ('one_more_field', lltype.Signed))

node2_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
node2_vtable_adr = llmemory.cast_ptr_to_adr(node2_vtable)


# ____________________________________________________________

class Loop(object):
    def __init__(self, operations):
        self.operations = operations

class Any(object):
    def __eq__(self, other):
        return True
    def __ne__(self, other):
        return False
    def __repr__(self):
        return '*'
ANY = Any()

def equaloplists(oplist1, oplist2):
    #saved = Box._extended_display
    #try:
    #    Box._extended_display = False
    print '-'*20, 'Comparing lists', '-'*20
    for op1, op2 in zip(oplist1, oplist2):
        txt1 = str(op1)
        txt2 = str(op2)
        while txt1 or txt2:
            print '%-39s| %s' % (txt1[:39], txt2[:39])
            txt1 = txt1[39:]
            txt2 = txt2[39:]
        assert op1.opnum == op2.opnum
        assert len(op1.args) == len(op2.args)
        for x, y in zip(op1.args, op2.args):
            assert x == y or y == x     # for ANY object :-(
        assert op1.result == op2.result
        assert op1.descr == op2.descr
    assert len(oplist1) == len(oplist2)
    print '-'*57
    #finally:
    #    Box._extended_display = saved
    return True

def ResOperation(opname, args, result, descr=None):
    if opname == 'escape':
        opnum = -123       # random number not in the list
    else:
        opnum = getattr(rop, opname.upper())
    return resoperation.ResOperation(opnum, args, result, descr)

# ____________________________________________________________

class A:
    ofs_next = runner.CPU.fielddescrof(NODE, 'next')
    ofs_value = runner.CPU.fielddescrof(NODE, 'value')
    size_of_node = runner.CPU.sizeof(NODE)
    #
    startnode = lltype.malloc(NODE)
    startnode.value = 20
    sum = BoxInt(0)
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, startnode))
    nextnode = lltype.malloc(NODE)
    nextnode.value = 19
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    n1nz = BoxInt(1)    # True
    v = BoxInt(startnode.value)
    v2 = BoxInt(startnode.value-1)
    sum2 = BoxInt(0 + startnode.value)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('jump', [sum2, n2], None),
        ]

def test_A_find_nodes():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    assert spec.nodes[A.sum] is not spec.nodes[A.sum2]
    assert spec.nodes[A.n1] is not spec.nodes[A.n2]
    assert spec.nodes[A.n1].cls.source.value == node_vtable_adr
    assert not spec.nodes[A.n1].escaped
    assert spec.nodes[A.n2].cls.source.value == node_vtable_adr
    assert not spec.nodes[A.n2].escaped

def test_A_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert len(spec.specnodes) == 2
    spec_sum, spec_n = spec.specnodes
    assert isinstance(spec_sum, NotSpecNode)
    assert isinstance(spec_n, VirtualInstanceSpecNode)
    assert spec_n.known_class.value == node_vtable_adr
    assert spec_n.fields[0][0] == A.ofs_value
    assert isinstance(spec_n.fields[0][1], NotSpecNode)

def test_A_optimize_loop():
    spec = PerfectSpecializer(Loop(A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [A.sum, A.v], None),
        ResOperation('int_sub', [A.v, ConstInt(1)], A.v2),
        ResOperation('int_add', [A.sum, A.v], A.sum2),
        ResOperation('jump', [A.sum2, A.v2], None),
        ])

# ____________________________________________________________

class B:
    locals().update(A.__dict__)    # :-)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('escape', [n1], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('escape', [n2], None),    # <== escaping
        ResOperation('jump', [sum2, n2], None),
        ]

def test_B_find_nodes():
    spec = PerfectSpecializer(Loop(B.ops))
    spec.find_nodes()
    assert spec.nodes[B.n1].cls.source.value == node_vtable_adr
    assert spec.nodes[B.n1].escaped
    assert spec.nodes[B.n2].cls.source.value == node_vtable_adr
    assert spec.nodes[B.n2].escaped

def test_B_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(B.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert len(spec.specnodes) == 2
    spec_sum, spec_n = spec.specnodes
    assert isinstance(spec_sum, NotSpecNode)
    assert type(spec_n) is FixedClassSpecNode
    assert spec_n.known_class.value == node_vtable_adr

def test_B_optimize_loop():
    spec = PerfectSpecializer(Loop(B.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [B.sum, B.n1], None),
        # guard_class is gone
        ResOperation('escape', [B.n1], None),
        ResOperation('getfield_gc', [B.n1], B.v, B.ofs_value),
        ResOperation('int_sub', [B.v, ConstInt(1)], B.v2),
        ResOperation('int_add', [B.sum, B.v], B.sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], B.n2,
                     B.size_of_node),
        ResOperation('setfield_gc', [B.n2, B.v2], None, B.ofs_value),
        ResOperation('escape', [B.n2], None),   # <== escaping
        ResOperation('jump', [B.sum2, B.n2], None),
        ])

# ____________________________________________________________

class C:
    locals().update(A.__dict__)    # :-)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('escape', [n1], None),    # <== escaping
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('escape', [n1], None),    # <== escaping
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('jump', [sum2, n2], None),
        ]

def test_C_find_nodes():
    spec = PerfectSpecializer(Loop(C.ops))
    spec.find_nodes()
    assert spec.nodes[C.n1].cls.source.value == node_vtable_adr
    assert spec.nodes[C.n1].escaped
    assert spec.nodes[C.n2].cls.source.value == node_vtable_adr

def test_C_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(C.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[C.n2].escaped
    assert len(spec.specnodes) == 2
    spec_sum, spec_n = spec.specnodes
    assert isinstance(spec_sum, NotSpecNode)
    assert type(spec_n) is FixedClassSpecNode
    assert spec_n.known_class.value == node_vtable_adr

def test_C_optimize_loop():
    spec = PerfectSpecializer(Loop(C.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [C.sum, C.n1], None),
        # guard_class is gone
        ResOperation('escape', [C.n1], None),   # <== escaping
        ResOperation('getfield_gc', [C.n1], C.v, C.ofs_value),
        ResOperation('int_sub', [C.v, ConstInt(1)], C.v2),
        ResOperation('int_add', [C.sum, C.v], C.sum2),
        ResOperation('escape', [C.n1], None),   # <== escaping
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], C.n2,
                     C.size_of_node),
        ResOperation('setfield_gc', [C.n2, C.v2], None, C.ofs_value),
        ResOperation('jump', [C.sum2, C.n2], None),
        ])

# ____________________________________________________________

class D:
    locals().update(A.__dict__)    # :-)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node2_vtable, cpu)], None),
        # the only difference is different vtable  ^^^^^^^^^^^^
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('jump', [sum2, n2], None),
        ]

def test_D_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(D.ops))
    spec.find_nodes()
    py.test.raises(CancelInefficientLoop, spec.intersect_input_and_output)

# ____________________________________________________________

class E:
    locals().update(A.__dict__)    # :-)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('guard_true', [v2], None),
        ResOperation('jump', [sum2, n2], None),
        ]
    ops[-2].liveboxes = [sum2, n2] 
        
def test_E_optimize_loop():
    spec = PerfectSpecializer(Loop(E.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [E.sum, E.v], None),
        # guard_class is gone
        ResOperation('int_sub', [E.v, ConstInt(1)], E.v2),
        ResOperation('int_add', [E.sum, E.v], E.sum2),
        ResOperation('guard_true', [E.v2], None),
        ResOperation('jump', [E.sum2, E.v2], None),
        ])
    guard_op = spec.loop.operations[-2]
    assert guard_op.getopname() == 'guard_true'
    assert guard_op.liveboxes == [E.sum2, E.v2]
    vt = cpu.cast_adr_to_int(node_vtable_adr)
    assert len(guard_op.unoptboxes) == 2
    assert guard_op.unoptboxes[0] == E.sum2
    assert len(guard_op.rebuild_ops) == 2
    assert guard_op.rebuild_ops[0].opnum == rop.NEW_WITH_VTABLE
    assert guard_op.rebuild_ops[1].opnum == rop.SETFIELD_GC
    assert guard_op.rebuild_ops[1].args[0] == guard_op.rebuild_ops[0].result
    assert guard_op.rebuild_ops[1].descr == E.ofs_value
    assert guard_op.unoptboxes[1] == guard_op.rebuild_ops[1].args[0]

def test_E_rebuild_after_failure():
    class FakeMetaInterp(object):
        def __init__(self):
            self.class_sizes = {cpu.cast_adr_to_int(node_vtable_adr):
                                E.size_of_node}
            self.cpu = cpu
            self.cpu.translate_support_code = False
            self.ops = []
        
        def execute_and_record(self, opnum, args, descr):
            self.ops.append((opnum, args, descr))
            return 'stuff'

    spec = PerfectSpecializer(Loop(E.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    guard_op = spec.loop.operations[-2]
    v_sum_b = BoxInt(13)
    v_v_b = BoxInt(14)
    fake_metainterp = FakeMetaInterp()
    newboxes = rebuild_boxes_from_guard_failure(guard_op, fake_metainterp,
                                                [v_sum_b, v_v_b])
    v_vt = ConstAddr(node_vtable_adr, cpu)
    expected = [
       (rop.NEW_WITH_VTABLE, [v_vt], ConstInt(-1)),    # "-1" is for testing
       (rop.SETFIELD_GC, ['stuff', v_v_b], E.ofs_value)
       ]
    assert expected == fake_metainterp.ops
    assert newboxes == [v_sum_b, 'stuff']

# ____________________________________________________________

class F:
    locals().update(A.__dict__)    # :-)
    nextnode = lltype.malloc(NODE)
    nextnode.value = 32
    n3 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    vbool1 = BoxInt(1)
    vbool2 = BoxInt(0)
    vbool3 = BoxInt(1)
    ops = [
        ResOperation('merge_point', [sum, n1, n3], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('ooisnot', [n2, n3], vbool1),
        ResOperation('guard_true', [vbool1], None),
        ResOperation('ooisnull', [n2], vbool2),
        ResOperation('guard_false', [vbool2], None),
        ResOperation('oononnull', [n3], vbool3),
        ResOperation('guard_true', [vbool3], None),        
        ResOperation('jump', [sum2, n2, n3], None),
        ]
    liveboxes = [sum2, n2, n3]
    ops[-2].liveboxes = liveboxes[:]
    ops[-4].liveboxes = liveboxes[:]
    ops[-6].liveboxes = liveboxes[:]

def test_F_find_nodes():
    spec = PerfectSpecializer(Loop(F.ops))
    spec.find_nodes()
    assert not spec.nodes[F.n1].escaped
    assert not spec.nodes[F.n2].escaped

def test_F_optimize_loop():
    spec = PerfectSpecializer(Loop(F.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[F.n3].escaped
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
            ResOperation('merge_point', [F.sum, F.v, F.n3], None),
            ResOperation('int_sub', [F.v, ConstInt(1)], F.v2),
            ResOperation('int_add', [F.sum, F.v], F.sum2),
            ResOperation('oononnull', [F.n3], F.vbool3),
            ResOperation('guard_true', [F.vbool3], None),        
            ResOperation('jump', [F.sum2, F.v2, F.n3], None),
        ])

class F2:
    locals().update(A.__dict__)    # :-)
    node2 = lltype.malloc(NODE)
    node3 = lltype.malloc(NODE)
    node4 = lltype.malloc(NODE)
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node2))
    n3 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node3))
    n4 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, node4))
    vbool1 = BoxInt(0)
    ops = [
        ResOperation('merge_point', [n2, n3], None),
        ResOperation('oois', [n2, n3], vbool1),
        ResOperation('guard_true', [vbool1], None),
        ResOperation('escape', [], n4),
        ResOperation('jump', [n2, n4], None),
        ]
    ops[2].liveboxes = [n2]

def test_F2_optimize_loop():
    spec = PerfectSpecializer(Loop(F2.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, F2.ops)

# ____________________________________________________________

class G:
    locals().update(A.__dict__)    # :-)
    v3 = BoxInt(123)
    v4 = BoxInt(124)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, ConstInt(123)], None, ofs_value),
        ResOperation('getfield_gc', [n2], v3, ofs_value),
        ResOperation('int_add', [v3, ConstInt(1)], v4),
        ResOperation('setfield_gc', [n2, v4], None, ofs_value),
        ResOperation('guard_true', [v2], None),
        ResOperation('jump', [sum2, n2], None),
        ]
    ops[-2].liveboxes = [sum2, n2] 

def test_G_optimize_loop():
    spec = PerfectSpecializer(Loop(G.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [G.sum, G.v], None),
        # guard_class is gone
        ResOperation('int_sub', [G.v, ConstInt(1)], G.v2),
        ResOperation('int_add', [G.sum, G.v], G.sum2),
        ResOperation('guard_true', [G.v2], None),
        ResOperation('jump', [G.sum2, ConstInt(124)], None),
        ])
    guard_op = spec.loop.operations[-2]
    assert guard_op.getopname() == 'guard_true'
    assert guard_op.liveboxes == [G.sum2, ConstInt(124)]
    vt = cpu.cast_adr_to_int(node_vtable_adr)
    assert ([op.getopname() for op in guard_op.rebuild_ops] ==
            ['new_with_vtable', 'setfield_gc'])

# ____________________________________________________________

class H:
    locals().update(A.__dict__)    # :-)
    #
    containernode = lltype.malloc(NODE)
    containernode.next = lltype.malloc(NODE)
    containernode.next.value = 20
    n0 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, containernode))
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, containernode.next))
    nextnode = lltype.malloc(NODE)
    nextnode.value = 19
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    v = BoxInt(containernode.next.value)
    v2 = BoxInt(nextnode.value)
    ops = [
        ResOperation('merge_point', [n0], None),
        ResOperation('getfield_gc', [n0], n1, ofs_next),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('setfield_gc', [n0, n2], None, ofs_next),
        ResOperation('jump', [n0], None),
        ]

def test_H_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(H.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[H.n0].escaped
    assert spec.nodes[H.n1].escaped
    assert spec.nodes[H.n2].escaped

# ____________________________________________________________

class I:
    locals().update(A.__dict__)    # :-)
    #
    containernode = lltype.malloc(NODE)
    containernode.next = lltype.malloc(NODE)
    containernode.next.value = 20
    n0 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, containernode))
    nextnode = lltype.malloc(NODE)
    nextnode.value = 19
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    ops = [
        ResOperation('merge_point', [n0], None),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, n0], None, ofs_next),
        ResOperation('jump', [n2], None),
        ]

def test_I_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(I.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[I.n0].escaped
    assert spec.nodes[I.n2].escaped

# ____________________________________________________________

class J:
    locals().update(A.__dict__)    # :-)
    #
    containernode = lltype.malloc(NODE)
    containernode.next = lltype.malloc(NODE)
    containernode.next.value = 20
    n0 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, containernode))
    nextnode = lltype.malloc(NODE)
    nextnode.value = 19
    n2 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    n1 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    ops = [
        ResOperation('merge_point', [n0], None),
        ResOperation('getfield_gc', [n0], n1, ofs_next),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, n1], None, ofs_next),
        ResOperation('jump', [n2], None),
        ]

def test_J_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(J.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert not spec.nodes[J.n0].escaped
    assert spec.nodes[J.n1].escaped
    assert not spec.nodes[J.n2].escaped

# ____________________________________________________________

class K0:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('getfield_gc', [n1], v3, ofs_value),
        ResOperation('int_add', [sum2, v3], sum3),
        ResOperation('escape', [n1], None),
        ResOperation('jump', [sum3, n1], None),
        ]

def test_K0_optimize_loop():
    spec = PerfectSpecializer(Loop(K0.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    v4 = spec.loop.operations[-1].args[-1]
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [K0.sum, K0.n1, K0.v], None),
        ResOperation('int_sub', [K0.v, ConstInt(1)], K0.v2),
        ResOperation('int_add', [K0.sum, K0.v], K0.sum2),
        ResOperation('int_add', [K0.sum2, K0.v], K0.sum3),
        ResOperation('escape', [K0.n1], None),
        ResOperation('getfield_gc', [K0.n1], v4, K0.ofs_value),
        ResOperation('jump', [K0.sum3, K0.n1, v4], None),
    ])


class K1:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('setfield_gc', [n1, sum], None, ofs_value),
        ResOperation('getfield_gc', [n1], v3, ofs_value),
        ResOperation('int_add', [sum2, v3], sum3),
        ResOperation('escape', [n1], None),
        ResOperation('jump', [sum3, n1], None),
        ]

def test_K1_optimize_loop():
    spec = PerfectSpecializer(Loop(K1.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    v4 = spec.loop.operations[-1].args[-1]
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [K1.sum, K1.n1, K1.v], None),
        ResOperation('int_sub', [K1.v, ConstInt(1)], K1.v2),
        ResOperation('int_add', [K1.sum, K1.v], K1.sum2),
        ResOperation('int_add', [K1.sum2, K1.sum], K1.sum3),
        ResOperation('setfield_gc', [K1.n1, K1.sum], None, K1.ofs_value),
        ResOperation('escape', [K1.n1], None),
        ResOperation('getfield_gc', [K1.n1], v4, K1.ofs_value),
        ResOperation('jump', [K1.sum3, K1.n1, v4], None),
    ])


class K:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('getfield_gc', [n1], v3, ofs_value),
        ResOperation('int_add', [sum2, v3], sum3),
        ResOperation('jump', [sum3, n1], None),
        ]

def test_K_optimize_loop():
    spec = PerfectSpecializer(Loop(K.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [K.sum, K.n1, K.v], None),
        ResOperation('int_sub', [K.v, ConstInt(1)], K.v2),
        ResOperation('int_add', [K.sum, K.v], K.sum2),
        ResOperation('int_add', [K.sum2, K.v], K.sum3),
        ResOperation('jump', [K.sum3, K.n1, K.v], None),
    ])

# ____________________________________________________________

class L:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('escape', [n1], None),
        ResOperation('getfield_gc', [n1], v3, ofs_value),
        ResOperation('int_add', [sum2, v3], sum3),
        ResOperation('jump', [sum3, n1], None),
        ]

def test_L_optimize_loop():
    spec = PerfectSpecializer(Loop(L.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [L.sum, L.n1, L.v], None),
        ResOperation('int_sub', [L.v, ConstInt(1)], L.v2),
        ResOperation('int_add', [L.sum, L.v], L.sum2),
        ResOperation('escape', [L.n1], None),
        ResOperation('getfield_gc', [L.n1], L.v3, L.ofs_value),
        ResOperation('int_add', [L.sum2, L.v3], L.sum3),
        ResOperation('jump', [L.sum3, L.n1, L.v3], None),
    ])

# ____________________________________________________________

class M:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('escape', [n1], None),
        ResOperation('jump', [sum2, n1], None),
        ]

def test_M_optimize_loop():
    spec = PerfectSpecializer(Loop(M.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    v4 = spec.loop.operations[-1].args[-1]
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [M.sum, M.n1, M.v], None),
        ResOperation('int_sub', [M.v, ConstInt(1)], M.v2),
        ResOperation('int_add', [M.sum, M.v], M.sum2),
        ResOperation('escape', [M.n1], None),
        ResOperation('getfield_gc', [M.n1], v4, M.ofs_value),
        ResOperation('jump', [M.sum2, M.n1, v4], None),
    ])

# ____________________________________________________________

class N:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        ResOperation('merge_point', [sum, n1], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('escape', [n1], None),
        ResOperation('jump', [sum2, n1], None),
        ]

def test_N_optimize_loop():
    spec = PerfectSpecializer(Loop(N.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    v4 = spec.loop.operations[-1].args[-1]
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [N.sum, N.n1, N.v], None),
        ResOperation('int_sub', [N.v, ConstInt(1)], N.v2),
        ResOperation('int_add', [N.sum, N.v], N.sum2),
        ResOperation('escape', [N.n1], None),
        ResOperation('getfield_gc', [N.n1], v4, N.ofs_value),
        ResOperation('jump', [N.sum2, N.n1, v4], None),
    ])

# ____________________________________________________________

class O1:
    locals().update(A.__dict__)    # :-)
    ops = [
        ResOperation('merge_point', [], None),
        ResOperation('escape', [], n1),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('jump', [], None),
        ]
    ops[-3].liveboxes = []
    ops[-2].liveboxes = []

def test_O1_optimize_loop():
    spec = PerfectSpecializer(Loop(O1.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [], None),
        ResOperation('escape', [], O1.n1),
        # only the first guard_class is left
        ResOperation('guard_class', [O1.n1, ConstAddr(node_vtable, cpu)],
                     None),
        ResOperation('jump', [], None),
    ])

# ____________________________________________________________

class O2:
    locals().update(A.__dict__)    # :-)
    v1 = BoxInt(1)
    ops = [
        ResOperation('merge_point', [], None),
        ResOperation('escape', [], n1),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('oononnull', [n1], v1),
        ResOperation('guard_true', [v1], None),
        ResOperation('jump', [], None),
        ]
    ops[-4].liveboxes = []
    ops[-2].liveboxes = []

def test_O2_optimize_loop():
    spec = PerfectSpecializer(Loop(O2.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [], None),
        ResOperation('escape', [], O2.n1),
        ResOperation('guard_class', [O2.n1, ConstAddr(node_vtable, cpu)],
                     None),
        # the oononnull and guard_true are gone, because we know they
        # return True -- as there was already a guard_class done on n1
        ResOperation('jump', [], None),
    ])

# ____________________________________________________________

class O3:
    locals().update(A.__dict__)    # :-)
    v1 = BoxInt(1)
    ops = [
        ResOperation('merge_point', [], None),
        ResOperation('escape', [], n1),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('oois', [n1, ConstPtr(lltype.nullptr(llmemory.GCREF.TO))],
                             v1),
        ResOperation('guard_false', [v1], None),
        ResOperation('jump', [], None),
        ]
    ops[-4].liveboxes = []
    ops[-2].liveboxes = []

def test_O3_optimize_loop():
    spec = PerfectSpecializer(Loop(O3.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('merge_point', [], None),
        ResOperation('escape', [], O3.n1),
        ResOperation('guard_class', [O3.n1, ConstAddr(node_vtable, cpu)],
                     None),
        # the oois and guard_false are gone, because we know they
        # return False -- as there was already a guard_class done on n1
        ResOperation('jump', [], None),
    ])

# ____________________________________________________________

class P:
    locals().update(A.__dict__)    # :-)
    thirdnode = lltype.malloc(NODE)
    n3 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, thirdnode))
    f = BoxInt(0)   # False
    ops = [
        ResOperation('merge_point', [n1, n3], None),
        ResOperation('getfield_gc', [n3], v, ofs_value),
        ResOperation('setfield_gc', [n1, ConstInt(1)], None, ofs_value),
        ResOperation('getfield_gc', [n3], v2, ofs_value),
        ResOperation('int_eq', [v, v2], f),
        ResOperation('guard_false', [f], None),
        ResOperation('getfield_gc', [n1], n2, ofs_next),
        ResOperation('jump', [n2, n3], None),
        ]
    ops[-3].liveboxes = []

def test_P_optimize_loop():
    py.test.skip("explodes")
    spec = PerfectSpecializer(Loop(P.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    # Optimization should not remove any operation.
    # If it does, then aliasing is not correctly detected.
    # It is ok to reorder just the 'getfield_gc[n1], n2' operation,
    # but the three remaining getfields/setfields *must* be in that order.
    equaloplists(spec.loop.operations, P.ops)
