
""" Tests for register allocation for common constructs
"""

import py
from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt
from pypy.jit.backend.x86.runner import CPU, GuardFailed
from pypy.rpython.lltypesystem import lltype
from pypy.jit.backend.x86.test.test_runner import FakeMetaInterp, FakeStats
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.x86.regalloc import RETURN

def test_simple_loop():
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    i = BoxInt(0) # a loop variable
    i_0 = BoxInt(0) # another incarnation of loop variable
    flag = BoxInt(1)  # True
    flag_0 = BoxInt(1)  # True
    # this should be more or less:
    # i = 0
    # while i < 5:
    #    i += 1
    operations = [
        ResOperation(rop.MERGE_POINT, [i, flag], None),
        ResOperation(rop.GUARD_TRUE, [flag], None),
        ResOperation(rop.INT_ADD, [i, ConstInt(1)], i_0),
        ResOperation(rop.INT_LT, [i_0, ConstInt(5)], flag_0),
        ResOperation(rop.JUMP, [i_0, flag_0], None),
        ]
    startmp = operations[0]
    operations[-1].jump_target = startmp
    operations[1].liveboxes = [i, flag]

    cpu.compile_operations(operations)
    res = cpu.execute_operations_in_new_frame('foo', operations,
                                              [BoxInt(0), BoxInt(1)])
    assert res.value == 5
    assert meta_interp.recordedvalues == [5, False]
    # assert stuff
    regalloc = cpu.assembler._regalloc
    # no leakage, args to merge_point
    assert regalloc.current_stack_depth == 2
    longevity = regalloc.longevity
    assert longevity == {i: (0, 2), flag: (0, 1), i_0: (2, 4), flag_0: (3, 4)}

def test_longer_loop():
    """ This test checks whether register allocation can
    reclaim back unused registers
    """
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    x = BoxInt(1)
    x0 = BoxInt(0)
    y = BoxInt(1)
    i = BoxInt(0)
    i0 = BoxInt(0)
    flag = BoxInt(1) # True
    flag0 = BoxInt(0) # False
    v0 = BoxInt(0)
    v1 = BoxInt(0)
    v2 = BoxInt(0)
    v3 = BoxInt(0)
    y0 = BoxInt(0)
    # code for:
    def f():
        i = 0
        x = 1
        y = 1
        while i < 5:
            x = ((y + x) * i) - x
            y = i * y - x * y
            i += 1
        return [x, y, i, i < 5]
    operations = [
        ResOperation(rop.MERGE_POINT, [x, y, i, flag], None),
        ResOperation(rop.GUARD_TRUE, [flag], None),
        ResOperation(rop.INT_ADD, [y, x], v0),
        ResOperation(rop.INT_MUL, [v0, i], v1),
        ResOperation(rop.INT_SUB, [v1, x], x0),
        ResOperation(rop.INT_MUL, [x0, y], v2),
        ResOperation(rop.INT_MUL, [i, y], v3),
        ResOperation(rop.INT_SUB, [v3, v2], y0),
        ResOperation(rop.INT_ADD, [i, ConstInt(1)], i0),
        ResOperation(rop.INT_LT, [i0, ConstInt(5)], flag0),
        ResOperation(rop.JUMP, [x0, y0, i0, flag0], None),
        ]
    startmp = operations[0]
    operations[-1].jump_target = startmp
    operations[1].liveboxes = [x, y, i, flag]

    cpu.compile_operations(operations)

    res = cpu.execute_operations_in_new_frame('foo', operations,
                                              [BoxInt(1), BoxInt(1),
                                               BoxInt(0), BoxInt(1)])
    assert res.value == 6
    assert meta_interp.recordedvalues == f()

def test_loop_with_const_and_var_swap():
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    x = BoxInt(0)
    y = BoxInt(0)
    z = BoxInt(0)
    i = BoxInt(0)
    i0 = BoxInt(0)
    v0 = BoxInt(0)
    operations = [
        ResOperation(rop.MERGE_POINT, [x, y, z, i], None),
        ResOperation(rop.INT_SUB, [i, ConstInt(1)], i0),
        ResOperation(rop.INT_GT, [i0, ConstInt(0)], v0),
        ResOperation(rop.GUARD_TRUE, [v0], None),
        ResOperation(rop.JUMP, [x, z, y, i0], None),
        ]
    operations[-1].jump_target = operations[0]
    operations[3].liveboxes = [x, y, z, i0]

    cpu.compile_operations(operations)

    res = cpu.execute_operations_in_new_frame('foo', operations,
                                                   [BoxInt(1), BoxInt(2),
                                                    BoxInt(3), BoxInt(10)])
    assert res.value == 1
    assert meta_interp.recordedvalues == [1, 3, 2, 0]

def test_bool_optimizations():
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    arg0 = BoxInt(3)
    arg1 = BoxInt(4)
    res = BoxInt(0)
    ops = [
        ResOperation(rop.MERGE_POINT, [arg0, arg1], None),
        ResOperation(rop.INT_GT, [arg0, arg1], res),
        ResOperation(rop.GUARD_TRUE, [res], None),
        # we should never get here
        ]
    ops[2].liveboxes = [res]

    cpu.compile_operations(ops)
    res = cpu.execute_operations_in_new_frame('foo', ops,
                                               [arg0, arg1])

    assert len(cpu.assembler._regalloc.computed_ops) == 2
    assert meta_interp.gf
    # er, what to check here, assembler???

def test_bool_cannot_optimize():
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    arg0 = BoxInt(3)
    arg1 = BoxInt(4)
    res = BoxInt(0)
    r = BoxInt(1)
    ops = [
        ResOperation(rop.MERGE_POINT, [arg0, arg1], None),
        ResOperation(rop.INT_GT, [arg0, arg1], res),
        ResOperation(rop.GUARD_TRUE, [res], None),
        # we should never get here
        ResOperation(rop.INT_ADD, [res, ConstInt(0)], r),
        ResOperation(RETURN, [r], None),
        ]
    ops[2].liveboxes = [res]

    cpu.compile_operations(ops)
    res = cpu.execute_operations_in_new_frame('foo', ops,
                                               [arg0, arg1])

    assert len(cpu.assembler._regalloc.computed_ops) == 5
    assert meta_interp.gf
    # er, what to check here, assembler???
