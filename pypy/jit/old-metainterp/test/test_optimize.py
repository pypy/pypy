import py
import copy

from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         ConstAddr, ResOperation, MergePoint,
                                         Jump, GuardOp)
from pypy.jit.metainterp.optimize import (PerfectSpecializer,
    CancelInefficientLoop, VirtualInstanceSpecNode, FixedClassSpecNode,
    rebuild_boxes_from_guard_failure, AllocationStorage,
    NotSpecNode)

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
        assert op1.opname == op2.opname
        assert len(op1.args) == len(op2.args)
        for x, y in zip(op1.args, op2.args):
            assert x == y or y == x     # for ANY object :-(
        assert op1.results == op2.results
    assert len(oplist1) == len(oplist2)
    print '-'*57
    #finally:
    #    Box._extended_display = saved
    return True

# ____________________________________________________________

class A:
    ofs_next = runner.CPU.fielddescrof(NODE, 'next')
    ofs_value = runner.CPU.fielddescrof(NODE, 'value')
    size_of_node = runner.CPU.sizeof(NODE)
    sizebox = ConstInt(size_of_node)
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
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('new_with_vtable', [sizebox,
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v2], []),
        Jump('jump', [sum2, n2], []),
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
        MergePoint('merge_point', [A.sum, A.v], []),
        ResOperation('int_sub', [A.v, ConstInt(1)], [A.v2]),
        ResOperation('int_add', [A.sum, A.v], [A.sum2]),
        Jump('jump', [A.sum2, A.v2], []),
        ])

# ____________________________________________________________

class B:
    locals().update(A.__dict__)    # :-)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('escape', [n1], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v2], []),
        ResOperation('some_escaping_operation', [n2], []),    # <== escaping
        Jump('jump', [sum2, n2], []),
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
        MergePoint('merge_point', [B.sum, B.n1], []),
        # guard_class is gone
        ResOperation('escape', [B.n1], []),
        ResOperation('getfield_gc', [B.n1, ConstInt(B.ofs_value)], [B.v]),
        ResOperation('int_sub', [B.v, ConstInt(1)], [B.v2]),
        ResOperation('int_add', [B.sum, B.v], [B.sum2]),
        ResOperation('new_with_vtable', [ConstInt(B.size_of_node),
                                         ConstAddr(node_vtable, cpu)], [B.n2]),
        ResOperation('setfield_gc', [B.n2, ConstInt(B.ofs_value), B.v2],
                                       []),
        ResOperation('some_escaping_operation', [B.n2], []),    # <== escaping
        Jump('jump', [B.sum2, B.n2], []),
        ])

# ____________________________________________________________

class C:
    locals().update(A.__dict__)    # :-)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('some_escaping_operation', [n1], []),    # <== escaping
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('some_escaping_operation', [n1], []),    # <== escaping
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v2], []),
        Jump('jump', [sum2, n2], []),
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
        MergePoint('merge_point', [C.sum, C.n1], []),
        # guard_class is gone
        ResOperation('some_escaping_operation', [C.n1], []),    # <== escaping
        ResOperation('getfield_gc', [C.n1, ConstInt(C.ofs_value)], [C.v]),
        ResOperation('int_sub', [C.v, ConstInt(1)], [C.v2]),
        ResOperation('int_add', [C.sum, C.v], [C.sum2]),
        ResOperation('some_escaping_operation', [C.n1], []),    # <== escaping
        ResOperation('new_with_vtable', [ConstInt(C.size_of_node),
                                         ConstAddr(node_vtable, cpu)], [C.n2]),
        ResOperation('setfield_gc', [C.n2, ConstInt(C.ofs_value), C.v2],
                                       []),
        Jump('jump', [C.sum2, C.n2], []),
        ])

# ____________________________________________________________

class D:
    locals().update(A.__dict__)    # :-)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node2_vtable, cpu),
                                     sizebox], []),
        # the only difference is different vtable  ^^^^^^^^^^^^
        ResOperation('getfield', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v2], []),
        Jump('jump', [sum2, n2], []),
        ]

def test_D_intersect_input_and_output():
    spec = PerfectSpecializer(Loop(D.ops))
    spec.find_nodes()
    py.test.raises(CancelInefficientLoop, spec.intersect_input_and_output)

# ____________________________________________________________

class E:
    locals().update(A.__dict__)    # :-)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v2], []),
        ResOperation('guard_true', [v2], []),
        Jump('jump', [sum2, n2], []),
        ]
    ops[-2].liveboxes = [sum2, n2] 
        
def test_E_optimize_loop():
    spec = PerfectSpecializer(Loop(E.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        MergePoint('merge_point', [E.sum, E.v], []),
        # guard_class is gone
        ResOperation('int_sub', [E.v, ConstInt(1)], [E.v2]),
        ResOperation('int_add', [E.sum, E.v], [E.sum2]),
        ResOperation('guard_true', [E.v2], []),
        Jump('jump', [E.sum2, E.v2], []),
        ])
    guard_op = spec.loop.operations[-2]
    assert guard_op.opname == 'guard_true'
    assert guard_op.liveboxes == [E.sum2, E.v2]
    vt = cpu.cast_adr_to_int(node_vtable_adr)
    assert guard_op.storage_info.allocations == [vt]
    assert guard_op.storage_info.setfields == [(0, E.ofs_value, -2)]

def test_E_rebuild_after_failure():
    class FakeHistory(object):
        def __init__(self):
            self.ops = []
        
        def execute_and_record(self, opname, args, res_type, pure):
            self.ops.append((opname, args))
            if res_type != 'void':
                return ['allocated']
            else:
                return []

    class FakeMetaInterp(object):
        def __init__(self):
            self.history = FakeHistory()
            self.class_sizes = {cpu.cast_adr_to_int(node_vtable_adr):
                                E.size_of_node}
    
    spec = PerfectSpecializer(Loop(E.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    guard_op = spec.loop.operations[-2]
    v_sum_b = BoxInt(13)
    v_v_b = BoxInt(14)
    vt = cpu.cast_adr_to_int(node_vtable_adr)
    fake_metainterp = FakeMetaInterp()
    newboxes = rebuild_boxes_from_guard_failure(guard_op, fake_metainterp,
                                                [v_sum_b, v_v_b])
    expected = [
       ('new_with_vtable', [E.sizebox, ConstInt(vt)]),
       ('setfield_gc', ['allocated', ConstInt(E.ofs_value), v_v_b])
       ]
    assert expected == fake_metainterp.history.ops
    assert newboxes == [v_sum_b, 'allocated']

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
        MergePoint('merge_point', [sum, n1, n3], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v2], []),
        ResOperation('ooisnot', [n2, n3], [vbool1]),
        GuardOp('guard_true', [vbool1], []),
        ResOperation('ooisnull', [n2], [vbool2]),
        GuardOp('guard_false', [vbool2], []),
        ResOperation('oononnull', [n3], [vbool3]),
        GuardOp('guard_true', [vbool3], []),        
        Jump('jump', [sum2, n2, n3], []),
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
            MergePoint('merge_point', [F.sum, F.v, F.n3], []),
            ResOperation('int_sub', [F.v, ConstInt(1)], [F.v2]),
            ResOperation('int_add', [F.sum, F.v], [F.sum2]),
            ResOperation('oononnull', [F.n3], [F.vbool3]),
            GuardOp('guard_true', [F.vbool3], []),        
            Jump('jump', [F.sum2, F.v2, F.n3], []),
        ])

# ____________________________________________________________

class G:
    locals().update(A.__dict__)    # :-)
    v3 = BoxInt(123)
    v4 = BoxInt(124)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value),
                                            ConstInt(123)], []),
        ResOperation('getfield_gc', [n2, ConstInt(ofs_value)], [v3]),
        ResOperation('int_add', [v3, ConstInt(1)], [v4]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v4], []),
        ResOperation('guard_true', [v2], []),
        Jump('jump', [sum2, n2], []),
        ]
    ops[-2].liveboxes = [sum2, n2] 

def test_G_optimize_loop():
    spec = PerfectSpecializer(Loop(G.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        MergePoint('merge_point', [G.sum, G.v], []),
        # guard_class is gone
        ResOperation('int_sub', [G.v, ConstInt(1)], [G.v2]),
        ResOperation('int_add', [G.sum, G.v], [G.sum2]),
        ResOperation('guard_true', [G.v2], []),
        Jump('jump', [G.sum2, ConstInt(124)], []),
        ])
    guard_op = spec.loop.operations[-2]
    assert guard_op.opname == 'guard_true'
    assert guard_op.liveboxes == [G.sum2, ConstInt(124)]
    vt = cpu.cast_adr_to_int(node_vtable_adr)
    assert guard_op.storage_info.allocations == [vt]
    assert guard_op.storage_info.setfields == [(0, G.ofs_value, -2)]

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
        MergePoint('merge_point', [n0], []),
        ResOperation('getfield_gc', [n0, ConstInt(ofs_next)], [n1]),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_value), v2], []),
        ResOperation('setfield_gc', [n0, ConstInt(ofs_next), n2], []),
        Jump('jump', [n0], []),
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
        MergePoint('merge_point', [n0], []),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_next), n0], []),
        Jump('jump', [n2], []),
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
        MergePoint('merge_point', [n0], []),
        ResOperation('getfield_gc', [n0, ConstInt(ofs_next)], [n1]),
        ResOperation('new_with_vtable', [ConstInt(size_of_node),
                                         ConstAddr(node_vtable, cpu)], [n2]),
        ResOperation('setfield_gc', [n2, ConstInt(ofs_next), n1], []),
        Jump('jump', [n2], []),
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
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v3]),
        ResOperation('int_add', [sum2, v3], [sum3]),
        ResOperation('escape', [n1], []),
        Jump('jump', [sum3, n1], []),
        ]

def test_K0_optimize_loop():
    spec = PerfectSpecializer(Loop(K0.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        MergePoint('merge_point', [K0.sum, K0.n1, K0.v], []),
        ResOperation('int_sub', [K0.v, ConstInt(1)], [K0.v2]),
        ResOperation('int_add', [K0.sum, K0.v], [K0.sum2]),
        ResOperation('int_add', [K0.sum2, K0.v], [K0.sum3]),
        ResOperation('escape', [K0.n1], []),
        ResOperation('getfield_gc', [K0.n1, ConstInt(K0.ofs_value)], [ANY]),
        Jump('jump', [K0.sum3, K0.n1, ANY], []),
    ])


class K1:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('setfield_gc', [n1, ConstInt(ofs_value), sum], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v3]),
        ResOperation('int_add', [sum2, v3], [sum3]),
        ResOperation('escape', [n1], []),
        Jump('jump', [sum3, n1], []),
        ]

def test_K1_optimize_loop():
    spec = PerfectSpecializer(Loop(K1.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        MergePoint('merge_point', [K1.sum, K1.n1, K1.v], []),
        ResOperation('int_sub', [K1.v, ConstInt(1)], [K1.v2]),
        ResOperation('int_add', [K1.sum, K1.v], [K1.sum2]),
        ResOperation('int_add', [K1.sum2, K1.sum], [K1.sum3]),
        ResOperation('setfield_gc', [K1.n1, ConstInt(K1.ofs_value), K1.sum],
                     []),
        ResOperation('escape', [K1.n1], []),
        ResOperation('getfield_gc', [K1.n1, ConstInt(K1.ofs_value)], [ANY]),
        Jump('jump', [K1.sum3, K1.n1, ANY], []),
    ])


class K:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v3]),
        ResOperation('int_add', [sum2, v3], [sum3]),
        Jump('jump', [sum3, n1], []),
        ]

def test_K_optimize_loop():
    spec = PerfectSpecializer(Loop(K.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        MergePoint('merge_point', [K.sum, K.n1, K.v], []),
        ResOperation('int_sub', [K.v, ConstInt(1)], [K.v2]),
        ResOperation('int_add', [K.sum, K.v], [K.sum2]),
        ResOperation('int_add', [K.sum2, K.v], [K.sum3]),
        Jump('jump', [K.sum3, K.n1, K.v], []),
    ])

# ____________________________________________________________

class L:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('escape', [n1], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v3]),
        ResOperation('int_add', [sum2, v3], [sum3]),
        Jump('jump', [sum3, n1], []),
        ]

def test_L_optimize_loop():
    spec = PerfectSpecializer(Loop(L.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        MergePoint('merge_point', [L.sum, L.n1, L.v], []),
        ResOperation('int_sub', [L.v, ConstInt(1)], [L.v2]),
        ResOperation('int_add', [L.sum, L.v], [L.sum2]),
        ResOperation('escape', [L.n1], []),
        ResOperation('getfield_gc', [L.n1, ConstInt(L.ofs_value)], [L.v3]),
        ResOperation('int_add', [L.sum2, L.v3], [L.sum3]),
        Jump('jump', [L.sum3, L.n1, L.v3], []),
    ])

# ____________________________________________________________

class M:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('escape', [n1], []),
        Jump('jump', [sum2, n1], []),
        ]

def test_M_optimize_loop():
    spec = PerfectSpecializer(Loop(M.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        MergePoint('merge_point', [L.sum, L.n1, L.v], []),
        ResOperation('int_sub', [L.v, ConstInt(1)], [L.v2]),
        ResOperation('int_add', [L.sum, L.v], [L.sum2]),
        ResOperation('escape', [L.n1], []),
        ResOperation('getfield_gc', [L.n1, ConstInt(L.ofs_value)], [ANY]),
        Jump('jump', [L.sum2, L.n1, ANY], []),
    ])


# ____________________________________________________________

class M:
    locals().update(A.__dict__)    # :-)
    sum3 = BoxInt(3)
    v3 = BoxInt(4)
    ops = [
        MergePoint('merge_point', [sum, n1], []),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu),
                                     sizebox], []),
        ResOperation('getfield_gc', [n1, ConstInt(ofs_value)], [v]),
        ResOperation('int_sub', [v, ConstInt(1)], [v2]),
        ResOperation('int_add', [sum, v], [sum2]),
        ResOperation('escape', [n1], []),
        Jump('jump', [sum2, n1], []),
        ]

def test_M_optimize_loop():
    spec = PerfectSpecializer(Loop(M.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        MergePoint('merge_point', [L.sum, L.n1, L.v], []),
        ResOperation('int_sub', [L.v, ConstInt(1)], [L.v2]),
        ResOperation('int_add', [L.sum, L.v], [L.sum2]),
        ResOperation('escape', [L.n1], []),
        ResOperation('getfield_gc', [L.n1, ConstInt(L.ofs_value)], [ANY]),
        Jump('jump', [L.sum2, L.n1, ANY], []),
    ])
