import py

from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE

from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import resoperation, history
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         Const, ConstAddr, TreeLoop)
from pypy.jit.metainterp.optimize4 import PerfectSpecializer
from pypy.jit.metainterp.specnode4 import (FixedClassSpecNode,
                                           NotSpecNode,
                                           VirtualInstanceSpecNode)

cpu = runner.LLtypeCPU(None)

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

cpu.class_sizes = {cpu.cast_adr_to_int(node_vtable_adr): cpu.sizeof(NODE)}


# ____________________________________________________________

def Loop(inputargs, operations):
    loop = TreeLoop("test")
    loop.inputargs = inputargs
    loop.operations = operations
    return loop

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


class CheckPerfectSpecializer(PerfectSpecializer):
    def optimize_loop(self):
        PerfectSpecializer.optimize_loop(self)
        check_operations(self.loop.inputargs, self.loop.operations)

def check_operations(inputargs, operations, indent=' |'):
    seen = dict.fromkeys(inputargs)
    for op in operations:
        print indent, op
        for x in op.args:
            assert x in seen or isinstance(x, Const)
        assert op.descr is None or isinstance(op.descr, history.AbstractDescr)
        if op.is_guard():
            check_operations(seen.keys(), op.suboperations, indent+'    ')
        if op.result is not None:
            seen[op.result] = True
    assert operations[-1].opnum in (rop.FAIL, rop.JUMP)

# ____________________________________________________________

class A:
    ofs_next = runner.LLtypeCPU.fielddescrof(NODE, 'next')
    ofs_value = runner.LLtypeCPU.fielddescrof(NODE, 'value')
    size_of_node = runner.LLtypeCPU.sizeof(NODE)
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
    inputargs = [sum, n1]
    ops = [
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, v2], None, ofs_value),
        ResOperation('jump', [sum2, n2], None),
        ]

    def set_guard(op, args):
        assert op.is_guard(), op
        op.suboperations = [ResOperation('fail', args, None)]

    set_guard(ops[0], [])

def test_A_find_nodes():
    spec = CheckPerfectSpecializer(Loop(A.inputargs, A.ops))
    spec.find_nodes()
    assert spec.nodes[A.sum] is not spec.nodes[A.sum2]
    assert spec.nodes[A.n1] is not spec.nodes[A.n2]
    assert spec.nodes[A.n1].cls.source.value == node_vtable_adr
    assert not spec.nodes[A.n1].escaped
    assert spec.nodes[A.n2].cls.source.value == node_vtable_adr
    assert not spec.nodes[A.n2].escaped

    assert len(spec.nodes[A.n1].curfields) == 0
    assert spec.nodes[A.n1].origfields[A.ofs_value] is spec.nodes[A.v]
    assert len(spec.nodes[A.n2].origfields) == 0
    assert spec.nodes[A.n2].curfields[A.ofs_value] is spec.nodes[A.v2]

def test_A_intersect_input_and_output():
    spec = CheckPerfectSpecializer(Loop(A.inputargs, A.ops))
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
    spec = CheckPerfectSpecializer(Loop(A.inputargs, A.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [A.sum, A.v]
    equaloplists(spec.loop.operations, [
        ResOperation('int_sub', [A.v, ConstInt(1)], A.v2),
        ResOperation('int_add', [A.sum, A.v], A.sum2),
        ResOperation('jump', [A.sum2, A.v2], None),
        ])

# ____________________________________________________________

class B:
    locals().update(A.__dict__)    # :-)
    inputargs = [sum, n1]
    ops = [
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
    set_guard(ops[0], [])

def test_B_find_nodes():
    spec = CheckPerfectSpecializer(Loop(B.inputargs, B.ops))
    spec.find_nodes()
    assert spec.nodes[B.n1].cls.source.value == node_vtable_adr
    assert spec.nodes[B.n1].escaped
    assert spec.nodes[B.n2].cls.source.value == node_vtable_adr
    assert spec.nodes[B.n2].escaped

def test_B_intersect_input_and_output():
    spec = CheckPerfectSpecializer(Loop(B.inputargs, B.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert len(spec.specnodes) == 2
    spec_sum, spec_n = spec.specnodes
    assert isinstance(spec_sum, NotSpecNode)
    assert type(spec_n) is FixedClassSpecNode
    assert spec_n.known_class.value == node_vtable_adr

def test_B_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(B.inputargs, B.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [B.sum, B.n1]
    equaloplists(spec.loop.operations, [
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
    inputargs = [sum, n1]
    ops = [
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
    set_guard(ops[0], [])

def test_C_find_nodes():
    spec = CheckPerfectSpecializer(Loop(C.inputargs, C.ops))
    spec.find_nodes()
    assert spec.nodes[C.n1].cls.source.value == node_vtable_adr
    assert spec.nodes[C.n1].escaped
    assert spec.nodes[C.n2].cls.source.value == node_vtable_adr

def test_C_intersect_input_and_output():
    spec = CheckPerfectSpecializer(Loop(C.inputargs, C.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[C.n2].escaped
    assert len(spec.specnodes) == 2
    spec_sum, spec_n = spec.specnodes
    assert isinstance(spec_sum, NotSpecNode)
    assert type(spec_n) is FixedClassSpecNode
    assert spec_n.known_class.value == node_vtable_adr

def test_C_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(C.inputargs, C.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [C.sum, C.n1]
    equaloplists(spec.loop.operations, [
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
    inputargs = [sum, n1]
    ops = [
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
    py.test.skip("nowadays, this compiles, just without making a virtual")
    spec = CheckPerfectSpecializer(Loop(D.inputargs, D.ops))
    spec.find_nodes()
    py.test.raises(CancelInefficientLoop, spec.intersect_input_and_output)

# ____________________________________________________________

class E:
    locals().update(A.__dict__)    # :-)
    inputargs = [sum, n1]
    ops = [
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
    set_guard(ops[0], [])
    set_guard(ops[-2], [sum2, n2])

def test_E_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(E.inputargs, E.ops), cpu=cpu)
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [E.sum, E.v]
    equaloplists(spec.loop.operations, [
        # guard_class is gone
        ResOperation('int_sub', [E.v, ConstInt(1)], E.v2),
        ResOperation('int_add', [E.sum, E.v], E.sum2),
        ResOperation('guard_true', [E.v2], None),
        ResOperation('jump', [E.sum2, E.v2], None),
        ])
    guard_op = spec.loop.operations[-2]
    assert guard_op.getopname() == 'guard_true'
    _, n2 = guard_op.suboperations[-1].args
    equaloplists(guard_op.suboperations, [
        ResOperation('new_with_vtable', [ConstAddr(node_vtable_adr, cpu)], n2,
                     E.size_of_node),
        ResOperation('setfield_gc', [n2, E.v2], None, E.ofs_value),
        ResOperation('fail', [E.sum2, n2], None),
        ])

##def test_E_rebuild_after_failure():
##    spec = CheckPerfectSpecializer(Loop(E.inputargs, E.ops), cpu=cpu)
##    spec.find_nodes()
##    spec.intersect_input_and_output()
##    spec.optimize_loop()
##    guard_op = spec.loop.operations[-2]
##    v_sum_b = BoxInt(13)
##    v_v_b = BoxInt(14)
##    history = History(cpu)
##    newboxes = rebuild_boxes_from_guard_failure(guard_op, cpu, history,
##                                                [v_sum_b, v_v_b])
##    assert len(newboxes) == 2
##    assert newboxes[0] == v_sum_b
##    p = newboxes[1].getptr(lltype.Ptr(NODE))
##    assert p.value == 14
##    assert len(history.operations) == 2
##    assert ([op.getopname() for op in history.operations] ==
##            ['new_with_vtable', 'setfield_gc'])

# ____________________________________________________________

class F:
    locals().update(A.__dict__)    # :-)
    nextnode = lltype.malloc(NODE)
    nextnode.value = 32
    n3 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, nextnode))
    vbool1 = BoxInt(1)
    vbool2 = BoxInt(0)
    vbool3 = BoxInt(1)
    inputargs = [sum, n1, n3]
    ops = [
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
    set_guard(ops[0], [])
    set_guard(ops[-2], [sum2, n2, n3])
    set_guard(ops[-4], [sum2, n2, n3])
    set_guard(ops[-6], [sum2, n2, n3])

def test_F_find_nodes():
    spec = CheckPerfectSpecializer(Loop(F.inputargs, F.ops))
    spec.find_nodes()
    assert not spec.nodes[F.n1].escaped
    assert not spec.nodes[F.n2].escaped

def test_F_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(F.inputargs, F.ops), cpu=cpu)
    spec.find_nodes()
    spec.intersect_input_and_output()
    assert spec.nodes[F.n3].escaped
    spec.optimize_loop()
    assert spec.loop.inputargs == [F.sum, F.v, F.n3]
    equaloplists(spec.loop.operations, [
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
    inputargs = [n2, n3]
    ops = [
        ResOperation('oois', [n2, n3], vbool1),
        ResOperation('guard_true', [vbool1], None),
        ResOperation('escape', [], n4),
        ResOperation('jump', [n2, n4], None),
        ]
    set_guard(ops[-3], [n2])

def test_F2_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(F2.inputargs, F2.ops), cpu=cpu)
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, F2.ops)

# ____________________________________________________________

class G:
    locals().update(A.__dict__)    # :-)
    v3 = BoxInt(123)
    v4 = BoxInt(124)
    inputargs = [sum, n1]
    ops = [
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
    set_guard(ops[0], [])
    set_guard(ops[-2], [sum2, n2])

def test_G_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(G.inputargs, G.ops), cpu=cpu)
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [G.sum, G.v]
    equaloplists(spec.loop.operations, [
        # guard_class is gone
        ResOperation('int_sub', [G.v, ConstInt(1)], G.v2),
        ResOperation('int_add', [G.sum, G.v], G.sum2),
        ResOperation('guard_true', [G.v2], None),
        ResOperation('jump', [G.sum2, ConstInt(124)], None),
        ])
    guard_op = spec.loop.operations[-2]
    assert guard_op.getopname() == 'guard_true'
    _, n2 = guard_op.suboperations[-1].args
    equaloplists(guard_op.suboperations, [
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     G.size_of_node),
        ResOperation('setfield_gc', [n2, ConstInt(124)], None, G.ofs_value),
        ResOperation('fail', [G.sum2, n2], None),
        ])

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
    inputargs = [n0]
    ops = [
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
    spec = CheckPerfectSpecializer(Loop(H.inputargs, H.ops))
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
    inputargs = [n0]
    ops = [
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, n0], None, ofs_next),
        ResOperation('jump', [n2], None),
        ]

def test_I_intersect_input_and_output():
    spec = CheckPerfectSpecializer(Loop(I.inputargs, I.ops))
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
    inputargs = [n0]
    ops = [
        ResOperation('getfield_gc', [n0], n1, ofs_next),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n2, n1], None, ofs_next),
        ResOperation('jump', [n2], None),
        ]

def test_J_intersect_input_and_output():
    spec = CheckPerfectSpecializer(Loop(J.inputargs, J.ops))
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
    inputargs = [sum, n1]
    ops = [
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
    py.test.skip("Disabled")
    spec = CheckPerfectSpecializer(Loop(K0.inputargs, K0.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    v4 = spec.loop.operations[-1].args[-1]
    assert spec.loop.inputargs == [K0.sum, K0.n1, K0.v]
    equaloplists(spec.loop.operations, [
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
    inputargs = [sum, n1]
    ops = [
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
    py.test.skip("Disabled")
    spec = CheckPerfectSpecializer(Loop(K1.inputargs, K1.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    v4 = spec.loop.operations[-1].args[-1]
    assert spec.loop.inputargs == [K1.sum, K1.n1, K1.v]
    equaloplists(spec.loop.operations, [
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
    inputargs = [sum, n1]
    ops = [
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('getfield_gc', [n1], v3, ofs_value),
        ResOperation('int_add', [sum2, v3], sum3),
        ResOperation('jump', [sum3, n1], None),
        ]

def test_K_optimize_loop():
    py.test.skip("Disabled")
    spec = CheckPerfectSpecializer(Loop(K.inputargs, K.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [K.sum, K.n1, K.v]
    equaloplists(spec.loop.operations, [
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
    inputargs = [sum, n1]
    ops = [
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
    py.test.skip("Disabled")
    spec = CheckPerfectSpecializer(Loop(L.inputargs, L.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == [L.sum, L.n1, L.v]
    equaloplists(spec.loop.operations, [
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
    inputargs = [sum, n1]
    ops = [
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('escape', [n1], None),
        ResOperation('jump', [sum2, n1], None),
        ]

def test_M_optimize_loop():
    py.test.skip("Disabled")
    spec = CheckPerfectSpecializer(Loop(M.inputargs, M.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    v4 = spec.loop.operations[-1].args[-1]
    assert spec.loop.inputargs == [M.sum, M.n1, M.v]
    equaloplists(spec.loop.operations, [
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
    inputargs = [sum, n1]
    ops = [
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('getfield_gc', [n1], v, ofs_value),
        ResOperation('int_sub', [v, ConstInt(1)], v2),
        ResOperation('int_add', [sum, v], sum2),
        ResOperation('escape', [n1], None),
        ResOperation('jump', [sum2, n1], None),
        ]

def test_N_optimize_loop():
    py.test.skip("Disabled")
    spec = CheckPerfectSpecializer(Loop(N.inputargs, N.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    v4 = spec.loop.operations[-1].args[-1]
    assert spec.loop.inputargs == [N.sum, N.n1, N.v]
    equaloplists(spec.loop.operations, [
        ResOperation('int_sub', [N.v, ConstInt(1)], N.v2),
        ResOperation('int_add', [N.sum, N.v], N.sum2),
        ResOperation('escape', [N.n1], None),
        ResOperation('getfield_gc', [N.n1], v4, N.ofs_value),
        ResOperation('jump', [N.sum2, N.n1, v4], None),
    ])

# ____________________________________________________________

class O1:
    locals().update(A.__dict__)    # :-)
    inputargs = []
    ops = [
        ResOperation('escape', [], n1),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('jump', [], None),
        ]
    set_guard(ops[-3], [])
    set_guard(ops[-2], [])

def test_O1_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(O1.inputargs, O1.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == []
    equaloplists(spec.loop.operations, [
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
    inputargs = []
    ops = [
        ResOperation('escape', [], n1),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('oononnull', [n1], v1),
        ResOperation('guard_true', [v1], None),
        ResOperation('jump', [], None),
        ]
    set_guard(ops[-4], [])
    set_guard(ops[-2], [])

def test_O2_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(O2.inputargs, O2.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == []
    equaloplists(spec.loop.operations, [
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
    inputargs = []
    ops = [
        ResOperation('escape', [], n1),
        ResOperation('guard_class', [n1, ConstAddr(node_vtable, cpu)], None),
        ResOperation('oois', [n1, ConstPtr(lltype.nullptr(llmemory.GCREF.TO))],
                             v1),
        ResOperation('guard_false', [v1], None),
        ResOperation('jump', [], None),
        ]
    set_guard(ops[-4], [])
    set_guard(ops[-2], [])

def test_O3_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(O3.inputargs, O3.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    assert spec.loop.inputargs == []
    equaloplists(spec.loop.operations, [
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
    inputargs = [n1, n3]
    ops = [
        ResOperation('getfield_gc', [n3], v, ofs_value),
        ResOperation('setfield_gc', [n1, ConstInt(1)], None, ofs_value),
        ResOperation('getfield_gc', [n3], v2, ofs_value),
        ResOperation('int_eq', [v, v2], f),
        ResOperation('guard_false', [f], None),
        ResOperation('getfield_gc', [n1], n2, ofs_next),
        ResOperation('jump', [n2, n3], None),
        ]
    set_guard(ops[-3], [])

def test_P_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(P.inputargs, P.ops))
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    # Optimization should not remove any operation.
    # If it does, then aliasing is not correctly detected.
    # It is ok to reorder just the 'getfield_gc[n1], n2' operation,
    # but the three remaining getfields/setfields *must* be in that order.
    equaloplists(spec.loop.operations, P.ops)

# ____________________________________________________________

class Q:
    locals().update(A.__dict__)    # :-)
    inputargs = [sum]
    ops = [
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n1,
                     size_of_node),
        ResOperation('setfield_gc', [n1, sum], None, ofs_value),
        ResOperation('getfield_gc', [n1], sum2, ofs_value),
        ResOperation('guard_true', [sum2], None),
        ResOperation('int_sub', [sum, ConstInt(1)], v),
        ResOperation('jump', [v], None),
        ]
    set_guard(ops[-3], [sum])

def test_Q_optimize_loop():
    spec = CheckPerfectSpecializer(Loop(Q.inputargs, Q.ops), cpu=cpu)
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, [
        ResOperation('guard_true', [Q.sum], None),
        ResOperation('int_sub', [Q.sum, ConstInt(1)], Q.v),
        ResOperation('jump', [Q.v], None),
        ])

# ____________________________________________________________

class R:
    locals().update(A.__dict__)    # :-)
    inputargs = [sum]
    ops = [
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n1,
                     size_of_node),
        ResOperation('int_is_true', [sum], n1nz),
        ResOperation('guard_true', [n1nz], None),
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n2,
                     size_of_node),
        ResOperation('setfield_gc', [n1, n2], None, ofs_next),
        ResOperation('int_sub', [sum, ConstInt(1)], sum2),
        ResOperation('jump', [sum2], None),
        ]
    set_guard(ops[2], [n1])

def test_R_find_nodes():
    spec = CheckPerfectSpecializer(Loop(R.inputargs, R.ops), cpu=cpu)
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()

# ____________________________________________________________

class S:
    locals().update(A.__dict__)    # :-)
    n1subnode = lltype.malloc(NODE2)
    n2subnode = lltype.malloc(NODE2)
    n1sub = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, n1subnode))
    n2sub = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, n2subnode))
    inputargs = [n1sub]
    ops = [
        ResOperation('guard_class', [n1sub, ConstAddr(node2_vtable, cpu)],
                     None),
        ResOperation('escape', [], n2sub),
        ResOperation('jump', [n2sub], None),
        ]
    set_guard(ops[0], [n1sub])

def test_S_find_nodes():
    py.test.skip("in-progress")
    spec = CheckPerfectSpecializer(Loop(S.inputargs, S.ops), cpu=cpu)
    spec.find_nodes()
    spec.intersect_input_and_output()
    spec.optimize_loop()
    equaloplists(spec.loop.operations, S.ops)
