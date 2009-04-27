
""" Tests for register allocation for common constructs
"""

import py
py.test.skip("Think about a nice way of doing stuff below")
from pypy.jit.backend.x86.test.test_runner import FakeMetaInterp, FakeStats
from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BoxPtr, ConstPtr
from pypy.jit.backend.x86.runner import CPU
from pypy.rpython.lltypesystem import lltype
from pypy.jit.metainterp.resoperation import rop
from pypy.rpython.lltypesystem import lltype, llmemory

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

    #assert len(cpu.assembler._regalloc.computed_ops) == 2
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

    #assert len(cpu.assembler._regalloc.computed_ops) == 5
    assert meta_interp.gf
    # er, what to check here, assembler???

def test_bug_1():
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    TP = lltype.GcStruct('x', ('y', lltype.Ptr(lltype.GcStruct('y'))))
    cpu.assembler._ovf_error_vtable = llmemory.cast_ptr_to_adr(lltype.nullptr(TP))
    cpu.assembler._ovf_error_inst = cpu.assembler._ovf_error_vtable
    
    p0 = BoxPtr()
    p1 = BoxPtr()
    i2 = BoxInt(1000)
    i3 = BoxInt(0)
    i4 = BoxInt(1)
    i5 = BoxInt(3)
    p6 = BoxPtr()
    p7 = BoxPtr()
    i8 = BoxInt(3)
    i9 = BoxInt(3)
    i10 = BoxInt(1)
    i11 = BoxInt(37)
    p12 = BoxPtr()
    p13 = BoxPtr()
    i14 = BoxInt()
    i15 = BoxInt()
    i16 = BoxInt()
    i17 = BoxInt()
    i18 = BoxInt()
    i19 = BoxInt()
    i20 = BoxInt()
    i21 = BoxInt()
    p22 = BoxPtr()
    i23 = BoxInt()
    none_ptr = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF,
                                               lltype.nullptr(TP)))
    const_code = none_ptr
    stuff = lltype.malloc(TP)
    stuff_2 = lltype.malloc(TP.y.TO)
    stuff.y = stuff_2
    const_ptr = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF,
                                                stuff))
    p12 = const_code.clonebox()
    const_name = none_ptr
    ops = [
        ResOperation(rop.MERGE_POINT, [p0, p1, i2, i3, i4, i5, p6, p7, i8,
                                       i9, i10, i11, p12, p13], None),
        ResOperation(rop.GUARD_VALUE, [ConstInt(1), i10], None),
        ResOperation(rop.OOISNULL, [p1], i14),
        ResOperation(rop.GUARD_TRUE, [i14], None),
        ResOperation(rop.INT_LT, [i5, ConstInt(0)], i15),
        ResOperation(rop.GUARD_FALSE, [i15], None),
        ResOperation(rop.INT_GE, [i5, i2], i16),
        ResOperation(rop.GUARD_FALSE, [i16], None),
        ResOperation(rop.INT_LT, [i5, ConstInt(0)], i17),
        ResOperation(rop.GUARD_FALSE, [i17], None),
        ResOperation(rop.INT_MUL, [i5, i4], i18),
        ResOperation(rop.INT_ADD, [i3, i18], i19),
        ResOperation(rop.INT_ADD, [i5, ConstInt(1)], i20),
        ResOperation(rop.INT_ADD_OVF, [i8, i19], i21),
        ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
        ResOperation(rop.GETFIELD_GC, [const_ptr], p22),
        ResOperation(rop.OOISNULL, [p22], i23),
        ResOperation(rop.GUARD_FALSE, [i23], None),
        ResOperation(rop.GUARD_VALUE, [p12, const_code], None),
        ResOperation(rop.JUMP, [p0, p1, i2, i3, i4, i20, none_ptr, none_ptr,
                                i21, i19, ConstInt(1), ConstInt(37), p12, p22],
                     None)
        ]
    ops[-5].descr = cpu.fielddescrof(TP, 'y')
    ops[1].liveboxes = [p0, i11, i5, i2, i3, i4, p1, p6, p7, i8,
                        i9, i10, p12, p13]
    ops[3].liveboxes = [p0, i5, i2, i3, i4, p1, p6, p7, i8, i9, p12, p13]
    ops[5].liveboxes = [p0, i5, i2, i3, i4, p1, p6, p7, i8, i9, p12, p13]
    ops[7].liveboxes = [p0, i5, i2, i3, i4, p1, p6, p7, i8, i9, p12, p13]
    ops[9].liveboxes = [p0, i5, i2, i3, i4, p1, p6, p7, i8, i9, p12, p13]
    ops[14].liveboxes = [p0, i20, i2, i3, i4, p1, i8, i19, p12, p13, i21]
    ops[17].liveboxes = [p0, i20, i2, i3, i4, p1, i21, i19, p12, p13, p22]
    ops[-2].liveboxes = [p0, i20, i2, i3, i4, p1, i21, i19, p12, p13, p22]

    ops[-1].jump_target = ops[0]
    cpu.compile_operations(ops)
    args = [p0, p1, i2, i3, i4, i5, p6, p7, i8, i9, i10, i11, p12, p13]
    res = cpu.execute_operations_in_new_frame('foo', ops, args)
    assert meta_interp.recordedvalues[1:3] == [1000, 1000]

def test_bug_2():
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    TP = lltype.GcStruct('x', ('y', lltype.Ptr(lltype.GcStruct('y'))))
    cpu.assembler._ovf_error_vtable = llmemory.cast_ptr_to_adr(lltype.nullptr(TP))
    cpu.assembler._ovf_error_inst = cpu.assembler._ovf_error_vtable
    ptr_0 = lltype.malloc(TP)
    ptr_0.y = lltype.malloc(TP.y.TO)
    ptr_1 = lltype.nullptr(TP)
    ptr_2 = lltype.nullptr(TP)
    ptr_3 = ptr_0
    ptr_4 = ptr_0
    boxptr_0 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_0))
    boxint_1 = BoxInt(780)
    boxint_2 = BoxInt(40)
    boxint_3 = BoxInt(37)
    boxptr_4 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_1))
    boxint_5 = BoxInt(40)
    boxint_6 = BoxInt(1000)
    boxint_7 = BoxInt(0)
    boxint_8 = BoxInt(1)
    boxptr_9 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_2))
    boxptr_10 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_2))
    boxptr_11 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_2))
    boxint_12 = BoxInt(1)
    boxptr_13 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_3))
    constint_14 = ConstInt(1)
    boxint_15 = BoxInt(1)
    constint_16 = ConstInt(0)
    boxint_17 = BoxInt(0)
    boxint_18 = BoxInt(0)
    boxint_19 = BoxInt(0)
    boxint_20 = BoxInt(40)
    boxint_21 = BoxInt(40)
    constint_22 = ConstInt(1)
    boxint_23 = BoxInt(41)
    boxint_24 = BoxInt(820)
    constptr_25 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_4))
    boxptr_26 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_3))
    boxint_27 = BoxInt(0)
    constptr_28 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_1))
    constint_29 = ConstInt(37)
    constptr_30 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_2))
    constint_31 = ConstInt(1)
    ops = [
        ResOperation(rop.MERGE_POINT, [boxptr_0, boxint_1, boxint_2, boxint_3, boxptr_4, boxint_5, boxint_6, boxint_7, boxint_8, boxptr_9, boxptr_10, boxptr_11, boxint_12, boxptr_13], None),
        ResOperation(rop.GUARD_VALUE, [boxint_12, constint_14], None),
        ResOperation(rop.OOISNULL, [boxptr_9], boxint_15),
        ResOperation(rop.GUARD_TRUE, [boxint_15], None),
        ResOperation(rop.INT_LT, [boxint_5, constint_16], boxint_17),
        ResOperation(rop.GUARD_FALSE, [boxint_17], None),
        ResOperation(rop.INT_GE, [boxint_5, boxint_6], boxint_18),
        ResOperation(rop.GUARD_FALSE, [boxint_18], None),
        ResOperation(rop.INT_LT, [boxint_5, constint_16], boxint_19),
        ResOperation(rop.GUARD_FALSE, [boxint_19], None),
        ResOperation(rop.INT_MUL, [boxint_5, boxint_8], boxint_20),
        ResOperation(rop.INT_ADD, [boxint_7, boxint_20], boxint_21),
        ResOperation(rop.INT_ADD, [boxint_5, constint_22], boxint_23),
        ResOperation(rop.INT_ADD_OVF, [boxint_1, boxint_21], boxint_24),
        ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
        ResOperation(rop.GETFIELD_GC, [constptr_25], boxptr_26),
        ResOperation(rop.OOISNULL, [boxptr_26], boxint_27),
        ResOperation(rop.GUARD_FALSE, [boxint_27], None),
        ResOperation(rop.GUARD_VALUE, [boxptr_4, constptr_28], None),
        ResOperation(rop.JUMP, [boxptr_0, boxint_24, boxint_21, constint_29, boxptr_4, boxint_23, boxint_6, boxint_7, boxint_8, boxptr_9, constptr_30, constptr_30, constint_31, boxptr_26], None),
    ]
    ops[-1].jump_target = ops[0]
    ops[-1].jump_target = ops[0]
    ops[1].liveboxes = []
    ops[3].liveboxes = []
    ops[5].liveboxes = []
    ops[7].liveboxes = []
    ops[9].liveboxes = []
    ops[-2].liveboxes = []
    ops[-3].liveboxes = []
    ops[-6].liveboxes = []
    ops[-5].descr = cpu.fielddescrof(TP, 'y')
    args = [boxptr_0, boxint_1, boxint_2, boxint_3, boxptr_4, boxint_5, boxint_6, boxint_7, boxint_8, boxptr_9, boxptr_10, boxptr_11, boxint_12, boxptr_13]
    cpu.compile_operations(ops)
    res = cpu.execute_operations_in_new_frame('foo', ops, args)

def test_bug_3():
    meta_interp = FakeMetaInterp()
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.set_meta_interp(meta_interp)
    TP = lltype.GcStruct('x', ('y', lltype.Ptr(lltype.GcStruct('y'))))
    cpu.assembler._ovf_error_vtable = llmemory.cast_ptr_to_adr(lltype.nullptr(TP))
    cpu.assembler._ovf_error_inst = cpu.assembler._ovf_error_vtable
    ptr_0 = lltype.malloc(TP)
    ptr_0.y = lltype.malloc(TP.y.TO)
    ptr_1 = lltype.nullptr(TP)
    ptr_2 = lltype.nullptr(TP)
    ptr_3 = ptr_0
    ptr_4 = ptr_0
    boxptr_0 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_0))
    boxint_1 = BoxInt(60)
    boxint_2 = BoxInt(40)
    boxint_3 = BoxInt(57)
    boxptr_4 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_1))
    boxint_5 = BoxInt(40)
    boxint_6 = BoxInt(100000000)
    boxint_7 = BoxInt(0)
    boxint_8 = BoxInt(1)
    boxptr_9 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_2))
    boxptr_10 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_2))
    boxptr_11 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_2))
    boxint_12 = BoxInt(1)
    boxptr_13 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_3))
    constint_14 = ConstInt(1)
    boxint_15 = BoxInt(1)
    constint_16 = ConstInt(0)
    boxint_17 = BoxInt(0)
    boxint_18 = BoxInt(0)
    boxint_19 = BoxInt(0)
    boxint_20 = BoxInt(40)
    boxint_21 = BoxInt(40)
    constint_22 = ConstInt(1)
    boxint_23 = BoxInt(41)
    constptr_24 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_1))
    constint_25 = ConstInt(2)
    boxint_26 = BoxInt(0)
    boxint_27 = BoxInt(42)
    boxint_28 = BoxInt(0)
    boxint_29 = BoxInt(0)
    boxint_30 = BoxInt(0)
    boxint_31 = BoxInt(0)
    boxint_32 = BoxInt(0)
    boxint_33 = BoxInt(0)
    constint_34 = ConstInt(2)
    boxint_35 = BoxInt(62)
    constptr_36 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_4))
    boxptr_37 = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_3))
    boxint_38 = BoxInt(0)
    constint_39 = ConstInt(57)
    constptr_40 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ptr_2))
    constint_41 = ConstInt(1)
    ops = [
        ResOperation(rop.MERGE_POINT, [boxptr_0, boxint_1, boxint_2, boxint_3, boxptr_4, boxint_5, boxint_6, boxint_7, boxint_8, boxptr_9, boxptr_10, boxptr_11, boxint_12, boxptr_13], None),
        ResOperation(rop.GUARD_VALUE, [boxint_12, constint_14], None),
        ResOperation(rop.OOISNULL, [boxptr_9], boxint_15),
        ResOperation(rop.GUARD_TRUE, [boxint_15], None),
        ResOperation(rop.INT_LT, [boxint_5, constint_16], boxint_17),
        ResOperation(rop.GUARD_FALSE, [boxint_17], None),
        ResOperation(rop.INT_GE, [boxint_5, boxint_6], boxint_18),
        ResOperation(rop.GUARD_FALSE, [boxint_18], None),
        ResOperation(rop.INT_LT, [boxint_5, constint_16], boxint_19),
        ResOperation(rop.GUARD_FALSE, [boxint_19], None),
        ResOperation(rop.INT_MUL, [boxint_5, boxint_8], boxint_20),
        ResOperation(rop.INT_ADD, [boxint_7, boxint_20], boxint_21),
        ResOperation(rop.INT_ADD, [boxint_5, constint_22], boxint_23),
        ResOperation(rop.GUARD_VALUE, [boxptr_4, constptr_24], None),
        ResOperation(rop.INT_MOD_OVF, [boxint_21, constint_25], boxint_26),
        ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
        ResOperation(rop.INT_XOR, [boxint_21, constint_25], boxint_27),
        ResOperation(rop.INT_LE, [boxint_27, constint_16], boxint_28),
        ResOperation(rop.INT_NE, [boxint_26, constint_16], boxint_29),
        ResOperation(rop.INT_AND, [boxint_28, boxint_29], boxint_30),
        ResOperation(rop.INT_MUL, [boxint_30, constint_25], boxint_31),
        ResOperation(rop.INT_ADD, [boxint_26, boxint_31], boxint_32),
        ResOperation(rop.INT_NE, [boxint_32, constint_16], boxint_33),
        ResOperation(rop.GUARD_FALSE, [boxint_33], None),
        ResOperation(rop.INT_ADD_OVF, [boxint_1, constint_34], boxint_35),
        ResOperation(rop.GUARD_NO_EXCEPTION, [], None),
        ResOperation(rop.GETFIELD_GC, [constptr_36], boxptr_37),
        ResOperation(rop.OOISNULL, [boxptr_37], boxint_38),
        ResOperation(rop.GUARD_FALSE, [boxint_38], None),
        ResOperation(rop.JUMP, [boxptr_0, boxint_35, boxint_21, constint_39, boxptr_4, boxint_23, boxint_6, boxint_7, boxint_8, boxptr_9, constptr_40, constptr_40, constint_41, boxptr_37], None),
    ]
    ops[-1].jump_target = ops[0]
    for op in ops:
        if op.is_guard():
            op.liveboxes = []
    ops[-4].descr = cpu.fielddescrof(TP, 'y')
    cpu.compile_operations(ops)
    args = [boxptr_0, boxint_1, boxint_2, boxint_3, boxptr_4, boxint_5, boxint_6, boxint_7, boxint_8, boxptr_9, boxptr_10, boxptr_11, boxint_12, boxptr_13]
    res = cpu.execute_operations_in_new_frame('foo', ops, args)
