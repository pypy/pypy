
from pypy.jit.metainterp.history import (BoxInt, BoxPtr, ConstInt, ConstPtr,
                                         Const, ConstAddr, TreeLoop)
from pypy.jit.metainterp.optimize4 import PerfectSpecializer
from pypy.jit.metainterp.test.test_optimize4 import A, ResOperation
from pypy.jit.metainterp.test.test_optimize4 import node_vtable, cpu

def Bridge(operations):
    loop = TreeLoop("test")
    loop.inputargs = None
    loop.operations = operations
    return loop

# ____________________________________________________________

class B:
    locals().update(A.__dict__)    # :-)
    ops = [
        ResOperation('new_with_vtable', [ConstAddr(node_vtable, cpu)], n1,
                     size_of_node),
        ResOperation('setfield_gc', [n2, n1], None, ofs_next),
        ResOperation('jump', [], None),
        ]

def test_B_find_nodes():
    spec = PerfectSpecializer(Bridge(B.ops))
    spec.find_nodes()
    spec.propagate_escapes()
    # 'n2' should be marked as 'escaped', so that 'n1' is too
    assert spec.nodes[B.n2].escaped
    assert spec.nodes[B.n1].escaped

# ____________________________________________________________

class C:
    locals().update(A.__dict__)    # :-)
    ops = [
        ResOperation('guard_value', [n1, ConstInt(1)], None),
        ResOperation('jump', [], None),
        ]
    set_guard(ops[0], [v])

def test_C_optimize_loop():
    spec = PerfectSpecializer(Bridge(C.ops))
    spec.find_nodes()
    spec.propagate_escapes()
    spec.specnodes = []
    spec.optimize_loop()
